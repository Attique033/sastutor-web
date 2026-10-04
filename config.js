// Loads config.json and renders every editable value into the page.
// Edit config.json, not the HTML. index.html waits on window.siteConfig before wiring up interactions.
(() => {
  const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const get = (obj, path) => path.split(".").reduce((o, k) => o?.[k], obj);
  const fill = (sel, html) => { const el = document.querySelector(sel); if (el) el.innerHTML = html; };
  const stars = '<span class="stars">★★★★★</span>';
  const badge = '<svg viewBox="0 0 24 24" fill="currentColor" aria-label="Verified"><path d="M12 2l2.4 2.2 3.2-.4.9 3.1 2.9 1.5-1 3.1 1 3.1-2.9 1.5-.9 3.1-3.2-.4L12 22l-2.4-2.2-3.2.4-.9-3.1-2.9-1.5 1-3.1-1-3.1 2.9-1.5.9-3.1 3.2.4z"/><path d="M8 12l3 3 5-6" stroke="#fff" stroke-width="2" fill="none"/></svg>';
  const crown = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 7l4.5 4L12 4l4.5 7L21 7l-2 12H5z"/></svg>';
  const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  function render(cfg) {
    // single values: <span data-cfg="business.enrolmentBanner"></span>
    document.querySelectorAll("[data-cfg]").forEach(el => { el.textContent = get(cfg, el.dataset.cfg) ?? ""; });

    // subject and level dropdowns in all three forms (the placeholder option stays in the HTML)
    const options = list => list.map(o => `<option>${esc(o)}</option>`).join("");
    document.querySelectorAll('select[name="subject"]').forEach(sel => sel.insertAdjacentHTML("beforeend", options(cfg.subjects)));
    // some subjects (e.g. Entry test) swap the level dropdown for their own list and label
    const setLevels = (sel, subject) => {
      const set = cfg.levelsBySubject?.[subject], label = sel.closest(".field")?.querySelector("label"), ph = sel.options[0];
      if (label) { label.dataset.orig ??= label.textContent; label.textContent = set?.label || label.dataset.orig; }
      ph.dataset.orig ??= ph.textContent; ph.textContent = set?.placeholder || ph.dataset.orig;
      sel.length = 1;
      sel.insertAdjacentHTML("beforeend", options(set?.options || cfg.levels));
      const goals = sel.form?.querySelector(".goal-chips");  // goal chips follow the subject too
      if (goals) goals.innerHTML = (set?.goals || cfg.goals).map((g, i) =>
        `<label><input type="radio" name="goal" value="${esc(g)}"${i ? "" : " checked"}><span>${esc(g)}</span></label>`).join("");
    };
    document.querySelectorAll('select[name="level"]').forEach(sel => setLevels(sel, ""));
    document.querySelectorAll('select[name="subject"]').forEach(sel => sel.addEventListener("change", () => {
      const level = sel.form?.elements.level;
      if (level) setLevels(level, sel.value);
    }));

    fill("#roster", cfg.tutors.map((t, i) =>
      `<button type="button" role="tab" data-jump="${i}" aria-label="Show ${esc(t.name)}"><img src="${esc(t.photo)}" alt="" width="52" height="52" loading="lazy"></button>`).join(""));

    fill("#deck", cfg.tutors.map(t => `
      <article class="fc" aria-label="${esc(t.name)}, ${esc(t.subject)} tutor"><div class="fc-in">
        <div class="face face-front">${t.badge ? `<span class="fc-badge">${crown}${esc(t.badge)}</span>` : ""}<img src="${esc(t.photo)}" alt="${esc(t.name)}, ${esc(t.subject)} tutor" width="600" height="720" loading="lazy" draggable="false">
          <div class="fc-body"><h3>${esc(t.name)} ${badge}</h3><p class="sub">${esc(t.credentials)}</p>
            <div class="tags">${t.subjects.map(x => `<span>${esc(x)}</span>`).join("")}${t.curricula.map(x => `<span class="c">${esc(x)}</span>`).join("")}</div></div></div>
        <div class="face face-back"><span class="eyebrow">How ${esc(t.name)} teaches</span><p class="style">${esc(t.style)}</p>
          <p class="best"><b>Best for</b> ${esc(t.bestFor)}</p><span class="flip-hint">Tap to flip back</span></div>
      </div></article>`).join(""));

    const b = cfg.business;
    fill("#wall", cfg.wall.map(w => {
      if (w.type === "stat") return `<div class="stat rv"><strong>${esc(w.value)}</strong><span>${esc(w.label)}</span></div>`;
      if (w.type === "instagram") return `<a class="ig rv" href="${esc(b.instagram)}" target="_blank" rel="noopener"><p>${esc(w.text)}</p><span>${esc(b.instagramHandle)} →</span></a>`;
      return `<figure class="review${w.featured ? " feature" : ""} rv">${stars}<blockquote>“${esc(w.quote)}”</blockquote>
        <figcaption class="who"><b>${esc(w.name[0])}</b><div><strong>${esc(w.name)}</strong><small>${esc(w.role)}</small></div></figcaption></figure>`;
    }).join(""));

    fill("#plans", cfg.plans.map(p => `
      <div class="plan${p.popular ? " pop" : ""} rv">${p.popular ? '<span class="badge">Most popular</span>' : ""}<h3>${esc(p.name)}</h3><p class="per">${esc(p.cadence)}</p>
        <div class="price">${esc(cfg.currency)}${esc(p.price)}<small> ${esc(cfg.priceUnit)}</small></div>
        <ul>${p.features.map(f => `<li>${esc(f)}</li>`).join("")}</ul>
        <button class="btn" data-open-trial data-src="plan-${slug(p.name)}">Start free trial</button></div>`).join(""));

    fill("#faq-list", cfg.faq.map((f, i) => `<details${i ? "" : " open"}><summary>${esc(f.q)}</summary><p>${esc(f.a)}</p></details>`).join(""));

    const links = list => list.map(l => `<li><a href="${esc(l.href)}">${esc(l.label)}</a></li>`).join("");
    fill("#foot-subjects", links(cfg.footer.subjects));
    // become-a-tutor form: subject/curriculum chips and experience options
    const chips = (sel, name, list) => fill(sel, list.map(o => `<label><input type="checkbox" name="${name}" value="${esc(o)}"><span>${esc(o)}</span></label>`).join(""));
    chips("#apply-subjects", "subjects", cfg.subjects.filter(x => x !== "Other"));
    chips("#apply-curricula", "curricula", cfg.curricula);
    document.querySelector("#a-exp")?.insertAdjacentHTML("beforeend", cfg.teachingExperience.map(o => `<option>${esc(o)}</option>`).join(""));
    return cfg;
  }

  window.siteConfig = fetch("config.json", { cache: "no-cache" })
    .then(r => { if (!r.ok) throw new Error(`config.json: HTTP ${r.status}`); return r.json(); })
    .then(render)
    .catch(err => {
      console.error("Could not load config.json:", err);
      if (location.protocol === "file:") {  // browsers block fetch() on pages opened straight from disk
        document.body.insertAdjacentHTML("afterbegin", '<div style="position:sticky;top:0;z-index:300;background:#7A1F17;color:#fff;font:600 14px/1.5 system-ui,sans-serif;padding:10px 16px;text-align:center">Content needs a local server to load. In this folder run <code style="background:rgba(255,255,255,.15);padding:2px 6px;border-radius:4px">python3 -m http.server 8000</code> and open <code style="background:rgba(255,255,255,.15);padding:2px 6px;border-radius:4px">http://localhost:8000</code></div>');
      }
      return null;
    });
})();
