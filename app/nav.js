/* Shared site menu: Story · Explore · How we did it + EN/ES. Same on the three pages.
   Usage: <script src="nav.js" data-active="story|explore|method" [data-mount="css selector"] [data-before="css selector"]></script>
   - Renders into data-mount (default: [data-site-nav]); with data-before it is inserted before that child of the mount.
   - Language: ?lang= in the URL, else English. Clicking EN/ES updates the URL and the links (so the choice follows the
     visitor across pages) and fires window event "site-lang" (detail = "en" | "es") for the page to re-render.
   - With data-mount (a bar built at runtime) the menu is mounted on window load and re-mounted if the bar is rebuilt.
     The three pages now reserve [data-site-nav]. No text with figures here (scripts/check_story_literals.py). */
(function () {
  "use strict";
  const me = document.currentScript;
  const cfg = { active: me.dataset.active || "story", mount: me.dataset.mount || "[data-site-nav]", before: me.dataset.before || null };
  const T = {
    en: { story: "Story", explore: "Explore", method: "How we did it", lang: "Language", menu: "Site sections" },
    es: { story: "Historia", explore: "Explorar", method: "Cómo lo hicimos", lang: "Idioma", menu: "Secciones del sitio" },
  };
  const PAGES = [["story", "index.html"], ["explore", "explorer.html"], ["method", "method.html"]];
  // English by default (Space Apps delivery); the choice travels in the links (?lang=es), it is not remembered
  let lang = new URLSearchParams(location.search).get("lang") || "en";
  if (!T[lang]) lang = "en";
  window.SiteNav = { get lang() { return lang; } };

  function render(host) {
    const t = T[lang];
    host.setAttribute("aria-label", t.menu);
    host.innerHTML = `<div class="sn-links">${PAGES.map(([k, href]) =>
      `<a href="${href}?lang=${lang}"${k === cfg.active ? ' aria-current="page"' : ""}>${t[k]}</a>`).join("")}</div>` +
      `<div class="sn-lang" role="group" aria-label="${t.lang}">${["en", "es"].map((l) =>
        `<button type="button" data-l="${l}" aria-pressed="${l === lang}">${l.toUpperCase()}</button>`).join("")}</div>`;
    host.querySelectorAll(".sn-lang button").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.l)));
  }
  function setLang(l) {
    if (!T[l] || l === lang) return;
    lang = l;
    const u = new URL(location.href); u.searchParams.set("lang", l); history.replaceState(null, "", u);
    document.querySelectorAll("nav.site-nav").forEach(render);
    window.dispatchEvent(new CustomEvent("site-lang", { detail: l }));
  }
  function mount() {
    const parent = document.querySelector(cfg.mount);
    if (!parent || parent.querySelector("nav.site-nav")) return;
    const host = document.createElement("nav");
    host.className = "site-nav";
    render(host);
    const ref = cfg.before ? parent.querySelector(cfg.before) : null;
    if (ref) parent.insertBefore(host, ref); else parent.appendChild(host);
  }
  if (cfg.mount === "[data-site-nav]") {
    // pages that reserve a container: mount right away
    const el = document.querySelector("[data-site-nav]");
    if (el) { el.classList.add("site-nav"); render(el); }
  } else {
    // a bar built at runtime: mount after load and again if the bar is rebuilt
    const go = () => { mount(); const bar = document.querySelector(cfg.mount)?.closest("nav") || document.body;
      new MutationObserver(mount).observe(bar, { childList: true, subtree: true }); };
    if (document.readyState === "complete") go(); else window.addEventListener("load", go);
  }
})();
