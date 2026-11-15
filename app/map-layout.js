/* Map-first presentation. Existing data, calculations and tour content stay in index.html. */
window.mountMapLayout = function (actions) {
  const $ = selector => document.querySelector(selector);
  const variant = document.body.dataset.layout;
  const map = $('#map'), panel = $('.explorer .panel'), tour = $('#guided-tour');
  const legend = $('#legend'), dateControls = $('#date-ctrl'), replay = $('#tour-start');
  const wrap = $('.wrap'), explore = $('#explore');
  const research = document.createElement('dialog');
  research.id = 'research-dialog';
  research.setAttribute('aria-labelledby', 'research-title');
  research.innerHTML = `<header class="research-header"><div><span class="eyebrow">Published study</span><h2 id="research-title">Study & results</h2></div><button class="btn" type="button" id="research-close">Close</button></header><nav class="research-nav" aria-label="Study sections"><button class="btn" data-section="study-intro">Overview</button><button class="btn" data-section="impact">Land & roads</button><button class="btn" data-section="forest">Under the trees</button><button class="btn" data-section="validation">Checks</button><button class="btn" data-section="method">How it works</button></nav><div class="research-body"></div>`;
  for (const node of [...wrap.children]) {
    if (node !== explore && node.id !== 'err') research.querySelector('.research-body').append(node);
  }
  document.body.append(research);
  const workspace = document.createElement('div'); workspace.id = 'workspace';
  const drawer = document.createElement('aside'); drawer.id = 'explorer-drawer'; drawer.hidden = true;
  drawer.setAttribute('aria-labelledby', 'drawer-title');
  drawer.innerHTML = `<header class="drawer-header"><div><span class="eyebrow">Choose what to see</span><h2 id="drawer-title">Explore the map</h2></div><button type="button" class="btn" id="drawer-close" aria-label="Close exploration panel">×</button></header>`;
  const drawerReplay=document.createElement('button');drawerReplay.type='button';drawerReplay.className='btn';drawerReplay.id='drawer-tour';drawerReplay.textContent='Replay tour';panel.prepend(drawerReplay);
  drawer.append(panel);
  const notes = document.createElement('details'); notes.id = 'tour-notes';
  notes.innerHTML = '<summary>Observation & limits</summary>';
  notes.append($('#tour-action'), $('#tour-evidence'));
  tour.querySelector('.tour-copy').after(notes);
  const question = document.createElement('p'); question.className = 'tour-question'; question.textContent = 'Where does the water remain?';
  tour.prepend(question);
  const waypoints = document.createElement('nav'); waypoints.id = 'tour-waypoints'; waypoints.setAttribute('aria-label', 'Guided tour steps');
  ['Before the storm', 'Possible flooding appears', 'The water recedes', 'Road exposure', 'Under the trees'].forEach((label, index) => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'waypoint';
    button.setAttribute('aria-label', `Step ${index + 1}: ${label}`);
    const number = document.createElement('b'); number.textContent = String(index + 1).padStart(2, '0');
    const text = document.createElement('span'); text.textContent = label; button.append(number, text);
    button.addEventListener('click', () => actions.onStep(index)); waypoints.append(button);
  });
  tour.append(waypoints);
  const freeTimeline = document.createElement('section'); freeTimeline.id = 'free-timeline';
  freeTimeline.setAttribute('aria-label', 'Observation timeline');
  freeTimeline.innerHTML = '<div class="timeline-heading"><span class="ctrl-label">Choose a date</span><span id="timeline-selection"></span><button class="btn" type="button" id="timeline-configure">Compare dates</button></div>';
  freeTimeline.append(dateControls);
  const mapLegend = document.createElement('div'); mapLegend.id = 'map-legend';
  mapLegend.innerHTML = '<span class="ctrl-label" id="map-key-title">Map key</span>'; mapLegend.append(legend);
  const satelliteContext = document.createElement('p'); satelliteContext.id = 'satellite-context'; satelliteContext.className = 'note'; satelliteContext.hidden = true;
  satelliteContext.textContent = 'Satellite basemap · Image dates vary; not the selected NISAR date.';
  mapLegend.append(satelliteContext);
  const scrim = document.createElement('button'); scrim.id = 'drawer-scrim'; scrim.hidden = true; scrim.type = 'button'; scrim.setAttribute('aria-label', 'Close exploration panel');
  workspace.append(map, tour, mapLegend, freeTimeline, scrim, drawer);
  explore.replaceChildren(workspace); explore.setAttribute('aria-label', 'Interactive NISAR flood explorer'); explore.removeAttribute('aria-labelledby');
  const header = $('nav.top'); header.setAttribute('aria-label', 'Explorer navigation');
  header.innerHTML = '<div class="in"><div class="app-brand"><span class="brand-mark" aria-hidden="true">≈</span><div><strong>After the Storm</strong><span>NISAR · Uruguay</span></div></div><p id="active-selection" aria-live="polite">Loading the published observations…</p><div class="app-actions"><button type="button" class="btn" id="sources-open">Sources & limits</button><button type="button" class="btn" id="research-open">Study & results</button><button type="button" class="btn" id="explorer-open" aria-controls="explorer-drawer" aria-expanded="false">Explore freely</button></div></div>';
  replay.textContent = 'Replay tour'; replay.disabled = true; replay.classList.add('replay-button'); header.querySelector('.app-actions').prepend(replay);
  let drawerOpen = false, wasTour = false, lastFocus = null, resizeFrame;
  const resize = () => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(actions.onResize); };
  const setDrawer = (open, focus = true) => {
    drawerOpen = open; workspace.dataset.drawer = String(open); drawer.hidden = !open;
    scrim.hidden = !open; $('#explorer-open').setAttribute('aria-expanded', String(open));
    $('#explorer-open').textContent=actions.getState().tourActive?'Explore freely':open?'Close tools':'Explore';
    if (open && focus) { lastFocus = document.activeElement; $('#drawer-close').focus({preventScroll:true}); }
    if (!open && focus) (lastFocus || $('#explorer-open')).focus({preventScroll:true});
    resize();
  };
  const setTour = active => {
    workspace.dataset.touring = String(active); document.body.dataset.touring = String(active);
    const showTimeline = !active && actions.getState().layer === 'date';
    freeTimeline.hidden = !showTimeline;
    workspace.dataset.timelineVisible = String(showTimeline);
    if (active && !wasTour) setDrawer(false, false);
    if (!active && wasTour) setDrawer(variant === 'sidebar', false);
    wasTour = active; resize();
  };
  const openSources = () => {
    openResearch('provenance');
    requestAnimationFrame(() => $('#provenance-title').focus({preventScroll:true}));
  };
  const openResearch = id => {
    if (!research.open) research.showModal();
    requestAnimationFrame(() => { const target = id && document.getElementById(id); if (target && research.contains(target)) target.scrollIntoView({block:'start',behavior:'instant'}); });
  };
  drawerReplay.addEventListener('click',()=>{setDrawer(false,false);actions.onStep(0);});
  $('#drawer-close').addEventListener('click', () => setDrawer(false));
  scrim.addEventListener('click', () => setDrawer(false));
  $('#explorer-open').addEventListener('click', () => { if (actions.getState().tourActive) { actions.onExit(); setDrawer(true); } else setDrawer(!drawerOpen); });
  $('#timeline-configure').addEventListener('click', () => { setDrawer(true); $('#chk-compare').focus({preventScroll:true}); });
  $('#sources-open').addEventListener('click', openSources);
  $('#research-open').addEventListener('click', () => openResearch('study-intro'));
  $('#research-close').addEventListener('click', () => research.close());
  research.querySelectorAll('[data-section]').forEach(button => button.addEventListener('click', () => openResearch(button.dataset.section)));
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && drawerOpen && !research.open) setDrawer(false); });
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]'); if (!link) return;
    const target = document.getElementById(link.getAttribute('href').slice(1));
    if (target && research.contains(target)) { event.preventDefault(); openResearch(target.id); }
  });
  research.addEventListener('click', event => {
    if (event.target.closest('.go,.ctxmap .zr,#pulse .card')) { research.close(); actions.onExit(); setDrawer(true, false); }
  });
  new ResizeObserver(resize).observe(map);
  const labels = {date:'Water by date',extent:'Flood extent',persist:'Days under water',retreat:'Date it dried',forest:'Under the trees'};
  const formatDate=date=>new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(date+'T12:00:00Z'));
  const update = () => {
    const state = actions.getState(); setTour(state.tourActive);
    const date = state.dates[state.di];
    workspace.dataset.layer=state.layer;
    $('#date-layer-help').hidden=state.layer!=='date';
    $('#map-key-title').textContent=state.layer==='date'&&!state.tourActive?'Where might flooding have occurred?':'Map key';
    $('#active-selection').textContent = `${state.zoneName} · ${labels[state.layer]}`;
    $('#timeline-selection').textContent = state.comparing ? `${formatDate(state.dates[state.beforeDi])} ↔ ${formatDate(date)}` : formatDate(date);
    replay.disabled = !state.mapReady; replay.textContent = state.tourActive ? 'Restart tour' : 'Replay tour';
    $('#tour-exit').textContent = 'Skip tour';
    $('#explorer-open').textContent = state.tourActive ? 'Explore freely' : drawerOpen ? 'Close tools' : 'Explore';
    waypoints.querySelectorAll('button').forEach((button, index) => { button.setAttribute('aria-current', index === state.tourStep ? 'step' : 'false'); button.dataset.complete = String(index < state.tourStep); });
  };
  setTour(true);
  const openTools=()=>{setDrawer(true);drawer.scrollTop=0;};
  return {update, setTour, openSources, openResearch, openTools};
};
