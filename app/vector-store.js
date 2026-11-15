/* Load exact prebuilt polygons, with bounded memory/disk caches and cancellable prefetch. */
window.createPublishedVectorStore = function ({fallback, manifestSource}) {
  const memory = new Map();
  const memoryLimit = 24 * 1024 * 1024, diskLimit = 64 * 1024 * 1024;
  let memoryBytes = 0, prefetchController = null, prefetchTimer = null, diskWrites = Promise.resolve();
  const cacheName = `nisar-display-vectors-v1:${new URL('.', location.href).pathname}`;
  const abort = signal => { if (signal?.aborted) throw new DOMException('The view changed.', 'AbortError'); };
  const indexPromise = fetch('data/vectors/index.json', {cache:'no-cache'})
    .then(response => { if (!response.ok) throw new Error('No prepared vector index'); return response.json(); })
    .then(async index => {
      if (window.crypto?.subtle && manifestSource) {
        const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(manifestSource));
        const hash = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2,'0')).join('');
        if (hash !== index.sourceManifestSha256) return null;
      }
      return index;
    })
    .catch(() => null);
  const diskPromise = (async () => {
    try {
      if (!window.isSecureContext || !window.caches) return null;
      const cache = await caches.open(cacheName), index = await indexPromise;
      if (!index || index.format !== 1) return null;
      const active = new Set(Object.values(index.entries).map(entry => new URL(`data/vectors/${entry.file}`, location.href).href));
      for (const request of await cache.keys()) if (!active.has(request.url)) await cache.delete(request);
      return cache;
    } catch { return null; } // Storage is optional, including in private browsing.
  })();
  function remember(key, data, bytes) {
    if (memory.has(key)) { memoryBytes -= memory.get(key).bytes; memory.delete(key); }
    memory.set(key, {data, bytes}); memoryBytes += bytes;
    while (memoryBytes > memoryLimit && memory.size > 1) {
      const oldest = memory.keys().next().value; memoryBytes -= memory.get(oldest).bytes; memory.delete(oldest);
    }
  }
  function save(cache, url, bytes) {
    if (!cache || bytes.byteLength > diskLimit) return;
    diskWrites = diskWrites.catch(() => {}).then(async () => {
      await cache.delete(url);
      await cache.put(url, new Response(bytes, {headers:{'Content-Type':'application/octet-stream', 'X-Vector-Bytes':String(bytes.byteLength)}}));
      const keys = await cache.keys(), sizes = [];
      let total = 0;
      for (const key of keys) {
        const response = await cache.match(key);
        const size = Number(response.headers.get('X-Vector-Bytes')) || 0;
        sizes.push([key,size]); total += size;
      }
      for (const [key,size] of sizes) { if (total <= diskLimit) break; await cache.delete(key); total -= size; }
    }).catch(() => {}); // Quota errors must not prevent the selected view from loading.
  }
  async function decode(bytes, entry, signal) {
    abort(signal);
    let body = new Response(bytes).body;
    // Some hosts automatically decompress .gz responses; accept both representations.
    if (bytes[0] === 31 && bytes[1] === 139) body = body.pipeThrough(new DecompressionStream('gzip'));
    const raw = await new Response(body).arrayBuffer();
    abort(signal);
    if (window.crypto?.subtle) {
      const digest = await crypto.subtle.digest('SHA-256', raw);
      const hash = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2,'0')).join('');
      if (hash !== entry.sha256) throw new Error('The prepared polygons failed their integrity check.');
    }
    const data = JSON.parse(new TextDecoder().decode(raw));
    if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Invalid prepared polygons.');
    return data;
  }
  async function load(url, corners, classes, {signal} = {}) {
    abort(signal);
    const index = await indexPromise;
    abort(signal);
    const key = url.replace(/^data\//, ''), entry = index?.entries?.[key];
    const signature = classes.map(({label,rgb}) => ({label,rgb}));
    if (!entry || index.format !== 1 || !window.DecompressionStream ||
        JSON.stringify(entry.corners) !== JSON.stringify(corners) || JSON.stringify(entry.classes) !== JSON.stringify(signature)) {
      const data = await fallback(url, corners, classes); abort(signal); return data;
    }
    const asset = new URL(`data/vectors/${entry.file}`, location.href).href;
    let data;
    if (memory.has(asset)) {
      const cached = memory.get(asset); memory.delete(asset); memory.set(asset,cached); data = cached.data;
    } else {
      const cache = await diskPromise;
      abort(signal);
      const cached = await cache?.match(asset).catch(() => null);
      if (cached) {
        try { data = await decode(new Uint8Array(await cached.arrayBuffer()), entry, signal); }
        catch (error) { abort(signal); await cache.delete(asset).catch(() => {}); }
      }
      if (!data) {
        const response = await fetch(asset, {signal});
        if (!response.ok) throw new Error('The prepared polygons could not load. Please retry.');
        const bytes = new Uint8Array(await response.arrayBuffer());
        data = await decode(bytes, entry, signal);
        save(cache, asset, bytes);
      }
      abort(signal); remember(asset, data, entry.jsonBytes);
    }
    // Colors belong to the active UI theme, not the persistent geometry cache.
    const colors = new Map(classes.map(entry => [entry.label, entry.color]));
    return {...data, features:data.features.map(feature => ({...feature, properties:{...feature.properties, color:colors.get(feature.properties.label) || feature.properties.color}}))};
  }
  function cancelPrefetch() {
    clearTimeout(prefetchTimer); prefetchController?.abort(); prefetchController = null;
  }
  function prefetch(views) {
    cancelPrefetch();
    if (navigator.connection?.saveData || /(^|-)2g$/.test(navigator.connection?.effectiveType || '')) return;
    const controller = new AbortController(); prefetchController = controller;
    // One background request at a time, only after the current map has finished rendering.
    prefetchTimer = setTimeout(async () => {
      const index = await indexPromise;
      if (!index || !window.DecompressionStream || controller.signal.aborted) return;
      for (const view of views.slice(0,3)) {
        if (controller.signal.aborted) break;
        try { await load(view.url, view.corners, view.classes, {signal:controller.signal}); }
        catch (error) { if (error.name === 'AbortError') break; }
      }
    }, 250);
  }
  return {load, prefetch, cancelPrefetch};
};
