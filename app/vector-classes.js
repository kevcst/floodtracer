/* Shared categorical mask decoding for the browser and static vector exporter. */
globalThis.nisarVectorClasses = function (view, legends, colors = {}) {
  const rgb = color => color.startsWith('#')
    ? [parseInt(color.slice(1, 3), 16), parseInt(color.slice(3, 5), 16), parseInt(color.slice(5, 7), 16)]
    : (color.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
  const make = (color, label, maskRGB = rgb(color)) => ({color, label, rgb: maskRGB});
  const flood = colors.flood || '#eb6834', still = colors.still || '#2a78d6';
  const previous = legends.previa || 'rgb(138,149,161)';
  if (view === 'date') return [make(flood, 'Candidate new water', [235,104,52]), make(still, 'Baseline water', [42,120,214]), make(previous, 'Already wet before the storm (10–14 Aug)', [138,149,161])];
  if (view === 'extent') return [make(flood, 'Published flood-extent classification', [235,104,52]), make(previous, 'Already wet before the storm (10–14 Aug)')];
  if (view === 'persist') return [...legends.persistencia.map(p => make(p.color, `Observed duration: ${p.rango} days`)), make(legends.sigue, 'No dry observation by the end of the published series')];
  if (view === 'retreat') return [...legends.retiro.map(p => make(p.color, `Published retreat interval: ${p.desde} to ${p.hasta}`)), make(legends.sigue, 'No dry observation by the end of the published series')];
  return [make('rgb(27,175,122)', 'Published riverside-forest signal classification')];
};
