"""Prepare verified road-name metadata without changing published analysis datasets.

Usage: .venv/bin/python scripts/enrich_road_names.py
Optional: --sources /path/to/MTOP/snapshots --offline
Dependencies: numpy, rasterio, shapely (already in requirements.txt).
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import numpy as np
import rasterio.warp
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
SERVICE = 'https://geoservicios.mtop.gub.uy/geoserver/caminerias_intendencias/wfs'
DEPARTMENTS = ['treinta_y_tres', 'rocha', 'cerro_largo', 'durazno', 'soriano', 'rio_negro']
METRICS = ['km_bajo_agua', 'dias_mid', 'dias_min', 'dias_max', 'sigue']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def clean(value):
    text = str(value or '').strip()
    return text if text.lower() not in ['', 'null', 'sin nombre', 'sin dato', 's/n'] else ''


def project(x, y, z=None):
    return rasterio.warp.transform('EPSG:4326', 'EPSG:32721', x, y)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=ROOT / 'data_nisar/contexto/road_names_mtop')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    args.sources.mkdir(parents=True, exist_ok=True)
    road_bytes = (ROOT / 'app/data/impacto/caminos.geojson').read_bytes()
    manifest_bytes = (ROOT / 'app/data/manifest.json').read_bytes()
    roads, manifest = json.loads(road_bytes), json.loads(manifest_bytes)
    records, snapshots = [], []
    for department in DEPARTMENTS:
        query = dict(service='WFS', version='1.0.0', request='GetFeature',
                     typeName='caminerias_intendencias:v_camineria_' + department,
                     srsName='EPSG:4326', outputFormat='application/json',
                     bbox='-58.14,-33.78,-53.28,-32.28,EPSG:4326')
        url = SERVICE + '?' + urllib.parse.urlencode(query)
        path = args.sources / (department + '.geojson')
        if not args.offline:
            with urllib.request.urlopen(url, timeout=45) as response:
                payload = response.read()
            json.loads(payload)  # Do not replace a snapshot with a server error page.
            path.write_bytes(payload)
        payload = path.read_bytes()
        data = json.loads(payload)
        snapshots.append(dict(department=department, url=url, sha256=sha(payload), features=len(data['features'])))
        for feature in data['features']:
            props = feature['properties']
            code, name = clean(props.get('codigo')), clean(props.get('nombre'))
            if not re.fullmatch(r'UY[A-Z0-9]{6,7}', code):
                code = ''
            if not code and not name:
                continue
            geometry = transform(project, shape(feature['geometry']))
            if geometry.is_empty:
                continue
            records.append(dict(key=code or department + ':' + name, code=code, name=name,
                                department=department, gid=props['gid'], geometry=geometry,
                                buffer=geometry.buffer(25)))
    tree = STRtree([record['buffer'] for record in records])
    matches = []
    for index, feature in enumerate(roads['features']):
        props = feature['properties']
        if not props['nombre'].startswith('Unnamed'):
            continue  # Preserve existing OSM names.
        geometry = transform(project, shape(feature['geometry']))
        groups = collections.defaultdict(list)
        for candidate in tree.query(geometry, predicate='intersects'):
            record = records[int(candidate)]
            groups[record['key']].append(record)
        ranked = []
        for key, group in groups.items():
            coverage = geometry.intersection(unary_union([record['buffer'] for record in group])).length / geometry.length
            ranked.append((coverage, key, group))
        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked:
            continue
        coverage, key, group = ranked[0]
        runner = ranked[1][0] if len(ranked) > 1 else 0
        if coverage < .95 or runner > .10:
            continue
        lines = [line for record in group for line in
                 (list(record['geometry'].geoms) if record['geometry'].geom_type == 'MultiLineString' else [record['geometry']])]
        distances, aligned = [], []
        for fraction in np.linspace(.03, .97, max(15, min(150, int(geometry.length / 40)))):
            point = geometry.interpolate(fraction, normalized=True)
            line = min(lines, key=lambda candidate: candidate.distance(point))
            position = line.project(point)
            a, b = (geometry.interpolate(max(0, fraction * geometry.length - 10)),
                    geometry.interpolate(min(geometry.length, fraction * geometry.length + 10)))
            u, v = line.interpolate(max(0, position - 10)), line.interpolate(min(line.length, position + 10))
            va, vb = np.array([b.x - a.x, b.y - a.y]), np.array([v.x - u.x, v.y - u.y])
            denominator = np.linalg.norm(va) * np.linalg.norm(vb)
            cosine = abs(float(np.dot(va, vb) / denominator)) if denominator else 0
            distances.append(line.distance(point))
            aligned.append(cosine >= np.cos(np.pi / 6))
        p95, direction = float(np.percentile(distances, 95)), float(np.mean(aligned))
        if p95 > 15 or direction < .90:
            continue
        names = collections.defaultdict(list)
        for record in group:
            if record['name']:
                names[record['name']].append(record['buffer'])
        named = sorted([(geometry.intersection(unary_union(buffers)).length / geometry.length, name)
                        for name, buffers in names.items()], reverse=True)
        name = named[0][1] if named and named[0][0] >= .90 else ''
        code = group[0]['code']
        source_gids = sorted({record['gid'] for record in group})
        departments = sorted({record['department'] for record in group})
        source_query = dict(service='WFS', version='1.0.0', request='GetFeature',
                            typeName='caminerias_intendencias:v_camineria_' + departments[0],
                            outputFormat='application/json', CQL_FILTER='gid IN (' + ','.join(map(str, source_gids)) + ')')
        label = f'{name} ({code})' if name and code else name or f'Road {code}'
        matches.append(dict(index=index, zone=props['zona'], original_name=props['nombre'], display_name=label,
                            official_name=name, official_code=code, source_gids=source_gids,
                            departments=departments, source_url=SERVICE + '?' + urllib.parse.urlencode(source_query),
                            coverage_pct=round(coverage * 100, 2), runner_up_pct=round(runner * 100, 2),
                            p95_distance_m=round(p95, 2), direction_agreement_pct=round(direction * 100, 2)))
    # Link table rows only when metrics, original label, length and rounded reference location identify one segment.
    linked = []
    by_index = {match['index']: match for match in matches}
    for zone, data in manifest['zonas'].items():
        for row_index, road in enumerate(data['caminos']):
            candidates = []
            for index, feature in enumerate(roads['features']):
                props = feature['properties']
                if props['zona'] != zone or props['nombre'] != road['nombre'] or props['clase'] != road['clase']:
                    continue
                if any(props[k] != road[k] for k in METRICS):
                    continue
                geom = shape(feature['geometry'])
                if abs(geom.centroid.x - road['lon']) > .0051 or abs(geom.centroid.y - road['lat']) > .0051:
                    continue
                length = transform(project, geom).length / 1000
                if abs(length - road['km']) <= max(.03, road['km'] * .015):
                    candidates.append(index)
            if len(candidates) == 1 and candidates[0] in by_index:
                linked.append(dict(zone=zone, row_index=row_index, segment_index=candidates[0]))
    output = dict(format=1, authority='MTOP / OPP', retrieved_at=datetime.now(timezone.utc).isoformat(),
                  source_roads_sha256=sha(road_bytes), source_manifest_sha256=sha(manifest_bytes),
                  source_road_count=len(roads['features']), sources=snapshots,
                  method=dict(crs='EPSG:32721', buffer_m=25, minimum_coverage_pct=95,
                              maximum_runner_up_pct=10, maximum_p95_distance_m=15,
                              maximum_direction_difference_degrees=30, minimum_direction_agreement_pct=90,
                              minimum_named_coverage_pct=90),
                  summary=dict(enriched_segments=len(matches), segments_with_official_names=sum(bool(m['official_name']) for m in matches),
                               segments_with_code_only=sum(not m['official_name'] for m in matches), linked_table_rows=len(linked)),
                  segments=matches, manifest_rows=linked)
    target = ROOT / 'app/data/impacto/road-identities.json'
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(output['summary'], indent=2))
    for match in matches:
        print(match['index'], match['zone'], match['display_name'], 'coverage', match['coverage_pct'])
    print('Only road-identities.json was written. Published geometries and analysis datasets were not changed.')


if __name__ == '__main__':
    main()
