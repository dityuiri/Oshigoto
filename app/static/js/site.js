// Per-panel language: ?work=ja&fan=en wins (shareable links), then the
// visitor's last choice, then the defaults baked into the HTML (work=en, fan=ja).
(function () {
  const params = new URLSearchParams(location.search);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };

  // no element ids "work"/"fan": a #fan hash must not make the browser jump to a panel
  const panelEl = name => document.querySelector(".panel." + name);

  function setLang(panel, l, remember) {
    const el = panelEl(panel);
    if (!el || (l !== "en" && l !== "ja")) return;
    el.dataset.lang = l;
    document.querySelectorAll(`.lang[data-panel=${panel}] button`)
      .forEach(b => b.classList.toggle("on", b.dataset.l === l));
    if (remember) store.set("lang:" + panel, l);
  }

  ["work", "fan"].forEach(p => {
    setLang(p, params.get(p) || store.get("lang:" + p) || panelEl(p).dataset.lang, false);
  });
  document.querySelectorAll(".lang").forEach(box => box.addEventListener("click", e => {
    const b = e.target.closest("button");
    if (b) setLang(box.dataset.panel, b.dataset.l, true);
  }));

  // mobile: お仕事 / 推し事 tabs. /#fan opens the fan side (shareable); switching
  // tabs rewrites the hash, so the address bar always links to the side on screen.
  function showSide(t, updateUrl) {
    if (t !== "work" && t !== "fan") return false;
    document.querySelectorAll(".tabs button").forEach(x => x.classList.toggle("on", x.dataset.t === t));
    panelEl("work").toggleAttribute("data-m-hidden", t !== "work");
    panelEl("fan").toggleAttribute("data-m-hidden", t !== "fan");
    if (updateUrl) history.replaceState(null, "", t === "fan" ? "#fan" : location.pathname + location.search);
    return true;
  }
  if (showSide(location.hash.slice(1))) window.scrollTo(0, 0);
  window.addEventListener("hashchange", () => { if (showSide(location.hash.slice(1))) window.scrollTo(0, 0); });
  document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => {
    showSide(b.dataset.t, true);
    window.scrollTo(0, 0);
  }));

  // 好き曲 group tabs; the "♪" link on an oshi card opens that group's tab
  function showGroup(g) {
    document.querySelectorAll(".gtabs button").forEach(b => b.classList.toggle("on", b.dataset.g === g));
    document.querySelectorAll(".gpanel").forEach(p => { p.hidden = p.dataset.g !== g; });
  }
  document.querySelector(".gtabs")?.addEventListener("click", e => {
    const b = e.target.closest("button");
    if (b) showGroup(b.dataset.g);
  });
  document.querySelectorAll(".songs-link").forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    showGroup(a.dataset.g);
    document.getElementById("songs-h")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }));

  // two oshi of one group share a card slot: the swap button shows the other one
  document.querySelectorAll(".stack .swap").forEach(b => b.addEventListener("click", () => {
    const card = b.parentElement;
    const next = card.nextElementSibling || card.parentElement.firstElementChild;
    card.hidden = true;
    next.hidden = false;
    next.querySelector(".swap")?.focus({ preventScroll: true });
  }));

  // mail button: the address ships reversed so naive scrapers don't pick it up
  document.querySelectorAll("[data-mail]").forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    location.href = "mailto:" + a.dataset.mail.split("").reverse().join("");
  }));
})();
