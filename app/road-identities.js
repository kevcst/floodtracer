/* Optional static road identification. Exposure values and geometry remain the published OSM data. */
window.loadIdentifiedRoads = async function (manifest, manifestSource) {
  const [response, identityResponse] = await Promise.all([
    fetch('data/impacto/caminos.geojson'),
    fetch('data/impacto/road-identities.json', {cache:'no-cache'}).catch(() => null)
  ]);
  if (!response.ok) throw new Error('The published roads could not load.');
  const roadSource = await response.text(), roads = JSON.parse(roadSource);
  try {
    if (!identityResponse?.ok || !window.crypto?.subtle) return roads;
    const identities = await identityResponse.json();
    if (identities.format !== 1 || identities.source_road_count !== roads.features.length) return roads;
    const hash = async text => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))), n => n.toString(16).padStart(2,'0')).join('');
    const [roadHash, manifestHash] = await Promise.all([hash(roadSource), hash(manifestSource)]);
    if (roadHash !== identities.source_roads_sha256) return roads;
    const metadata = new Map();
    for (const segment of identities.segments) {
      const properties = roads.features[segment.index]?.properties;
      if (!properties || properties.zona !== segment.zone || properties.nombre !== segment.original_name) continue;
      const fields = {
        display_name:segment.display_name, official_name:segment.official_name,
        official_code:segment.official_code, identification_source:identities.authority,
        identification_source_url:segment.source_url, identification_retrieved_at:identities.retrieved_at
      };
      Object.assign(properties, fields); metadata.set(segment.index, fields);
    }
    if (manifestHash === identities.source_manifest_sha256) {
      for (const row of identities.manifest_rows) {
        const road = manifest.zonas[row.zone]?.caminos[row.row_index], fields = metadata.get(row.segment_index);
        if (road && fields) Object.assign(road, fields);
      }
    }
  } catch (error) {
    console.warn('Optional road identification is unavailable; using the published OSM labels.', error);
  }
  return roads;
};
