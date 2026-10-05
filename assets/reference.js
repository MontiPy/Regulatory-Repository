// Reference views for certification engineers: market profiles, the
// requirement crosswalk, the launch planner and the glossary.
//
// Data comes from the curated knowledge layer (knowledge/*.yaml → build.py →
// data/markets.json, crosswalk.json, glossary.json). app.js owns routing and
// calls RefViews.render(view, params) whenever ?view=<ref view> is active; this
// module renders into #ref-view and navigates through window.RegApp.
(function () {
  "use strict";

  const app = () => window.RegApp;
  const esc = (v) => app().escapeHtml(v);
  const root = document.querySelector("#ref-view");

  let K = null;          // loaded knowledge
  let loading = null;

  const PT_LABELS = { ICE: "Combustion (ICE)", HEV: "Hybrid (HEV)", PHEV: "Plug-in hybrid (PHEV)", BEV: "Battery electric (BEV)", FCEV: "Fuel cell (FCEV)" };
  const STATUS_LABELS = { "phase-in": "Phase-in", proposed: "Proposed", voluntary: "Voluntary", none: "No requirement" };
  const CONF_TIPS = {
    high: "Stable, well-documented regime. Still verify instrument versions before use.",
    medium: "Structure is right; specific instruments or dates may have moved. Verify with the authority.",
    low: "Thin public documentation — treat as a starting pointer only and confirm locally.",
  };
  const PLANNER_PRESETS = [
    { label: "North America", codes: ["US", "CA", "MX"] },
    { label: "Global top 10", codes: ["US", "CN", "EU", "JP", "IN", "KR", "BR", "CA", "AU", "GB"] },
    { label: "Asia-Pacific", codes: ["JP", "KR", "CN", "TW", "AU", "NZ", "TH", "MY", "ID", "PH", "VN", "SG", "IN"] },
    { label: "Gulf & Middle East", codes: ["SA", "AE", "GCC-OTHER", "IL", "TR"] },
    { label: "Latin America", codes: ["MX", "BR", "AR", "CL", "CO", "ANDEAN"] },
  ];

  function load() {
    if (loading) return loading;
    loading = Promise.all(["markets", "crosswalk", "glossary"].map((n) =>
      fetch(`data/${n}.json`).then((r) => { if (!r.ok) throw new Error(`${n}.json ${r.status}`); return r.json(); })
    )).then(([markets, crosswalk, glossary]) => {
      K = {
        markets,
        crosswalk,
        glossary,
        marketByCode: new Map(markets.markets.map((m) => [m.code, m])),
        topicById: new Map(crosswalk.topics.map((t) => [t.id, t])),
        colByKey: new Map(crosswalk.columns.map((c) => [c.key, c])),
      };
      return K;
    });
    return loading;
  }

  // ── small render helpers ─────────────────────────────────────────────
  function navLink(search, text, cls) {
    return `<a href="?${esc(search)}" data-nav-href="${esc(search)}"${cls ? ` class="${cls}"` : ""}>${text}</a>`;
  }

  function recordChip(id, backLabel) {
    const rec = app().record(id);
    if (!rec) return "";
    const label = shortCitation(rec);
    return `<a class="rec-chip" href="?id=${encodeURIComponent(id)}" data-record="${esc(id)}" data-back="${esc(backLabel || "Back")}" title="${esc(rec.title || id)}">${esc(label)}</a>`;
  }

  // CELEX 32018R0858 → "Reg. (EU) 2018/858"; CELEX 32007R0715 → "Reg. (EC) 715/2007"
  // (regulations were numbered number/year before 2015); directives are year/number.
  function celexLabel(citation) {
    const m = /^CELEX 3(\d{4})([RL])0*(\d+)$/.exec(citation);
    if (!m) return null;
    const [, year, kind, num] = m;
    if (kind === "L") return `Dir. ${year}/${num}`;
    const body = Number(year) >= 2010 ? "EU" : "EC";   // "(EU)" since the Lisbon Treaty
    return Number(year) >= 2015 ? `Reg. (${body}) ${year}/${num}` : `Reg. (${body}) ${num}/${year}`;
  }

  function shortCitation(rec) {
    const celex = celexLabel(String(rec.citation || ""));
    if (celex) return celex;
    let c = String(rec.citation || rec.id).replace(/^MVSR C\.R\.C\.,_c\._1038 s\. /, "CMVSS ").replace(/^49 CFR §571\./, "FMVSS ");
    if (c.length > 34) c = c.slice(0, 32) + "…";
    return c;
  }

  function recordChips(ids, backLabel, max) {
    const list = (ids || []).filter((id) => app().record(id));
    if (!list.length) return "";
    const limit = max || list.length;
    const shown = list.slice(0, limit).map((id) => recordChip(id, backLabel)).join("");
    const more = list.length > limit ? `<span class="rec-more" title="${esc(list.slice(limit).join(", "))}">+${list.length - limit}</span>` : "";
    return `<span class="rec-chips">${shown}${more}</span>`;
  }

  function regimeBadge(m) {
    const tip = (K.markets.regime_descriptions || {})[m.regime] || "";
    return `<span class="badge regime regime-${esc(m.regime)}" title="${esc(tip)}">${esc(m.regime_label)}</span>`;
  }

  function unBadge(label, value) {
    const cls = value === true ? "yes" : value === false ? "no" : "unk";
    const txt = value === true ? "✓" : value === false ? "✕" : "?";
    const tip = value === true ? `Contracting party to the UN ${label} Agreement`
      : value === false ? `Not a contracting party to the UN ${label} Agreement`
      : `UN ${label} Agreement status not verified — check UNECE`;
    return `<span class="badge un un-${cls}" title="${esc(tip)}">UN ${esc(label)} ${txt}</span>`;
  }

  function confBadge(level) {
    return `<span class="badge conf conf-${esc(level)}" tabindex="0" data-tooltip="${esc(CONF_TIPS[level] || "")}">${esc(level)} confidence</span>`;
  }

  function statusBadge(status) {
    if (!status || status === "mandatory") return "";
    return `<span class="badge cell-status st-${esc(status)}">${esc(STATUS_LABELS[status] || status)}</span>`;
  }

  function caveat(extra) {
    return `<p class="ref-caveat" role="note"><strong>Curated reference, not legal advice.</strong> ${extra || ""}Confirm the current instrument, series and transitional dates with the authority before any certification decision.</p>`;
  }

  function recordCountFor(m) {
    const regions = new Set(m.regions || []);
    if (!regions.size) return 0;
    return app().records().filter((r) => regions.has(r.region)).length;
  }

  function countriesCovered() {
    return K.markets.markets.reduce((n, m) => n + Math.max(1, (m.members || []).length), 0);
  }

  function matchesWord(text, q) {
    if (!q) return true;
    return String(text || "").toLowerCase().includes(q);
  }

  function marketHaystack(m) {
    return [m.code, m.name, m.basis, m.group, m.regime_label, ...(m.aliases || []), ...(m.members || []),
      ...(m.authorities || []).map((a) => a.name)].join(" ").toLowerCase();
  }

  // Which crosswalk column best represents a market's requirements?
  //   direct — the market has its own column (US, CN, SA→GCC …)
  //   via    — the market applies another regime (UN R / GSO) as its basis
  function columnForMarket(code) {
    const direct = K.crosswalk.columns.find((c) => c.market === code && c.key !== "UN");
    if (direct) return { col: direct, via: "" };
    if (code === "AE" || code === "GCC-OTHER") return { col: K.colByKey.get("GCC"), via: "GSO" };
    const m = K.marketByCode.get(code);
    if (m && (m.un_1958 === true || code === "EFTA" || code === "GB")) return { col: K.colByKey.get("UN"), via: "UN R" };
    return null;
  }

  function setTitle(text) {
    document.title = `${text} — Regulatory Repository`;
  }

  // Replace the current URL without re-rendering (filter inputs).
  function replaceParams(params) {
    const qs = params.toString();
    history.replaceState(history.state, "", qs ? `${window.location.pathname}?${qs}` : window.location.pathname);
  }

  // ── Markets directory ────────────────────────────────────────────────
  function renderMarkets(params) {
    setTitle("Market profiles");
    const regimes = K.markets.regimes;
    root.innerHTML = `
      <div class="ref-wrap">
        <header class="ref-head">
          <p class="ref-eyebrow">Market profiles</p>
          <h1 class="ref-title">How do I get a vehicle approved in…?</h1>
          <p class="ref-lede">${K.markets.markets.length} profiles covering ${countriesCovered()} countries and territories: certification regime, authorities, accepted foreign approvals, required marks, emissions level, language and process. Click a market for its full profile and requirement map.</p>
          ${caveat()}
        </header>
        <div class="ref-controls">
          <input type="search" id="mk-q" class="ref-input" placeholder="Filter by country, authority, or regime (e.g. Germany, SASO, self-cert)…" aria-label="Filter markets" value="${esc(params.get("q") || "")}">
          <select id="mk-regime" class="ref-select" aria-label="Filter by regime">
            <option value="">All regimes</option>
            ${Object.entries(regimes).map(([k, v]) => `<option value="${esc(k)}"${params.get("regime") === k ? " selected" : ""}>${esc(v)}</option>`).join("")}
          </select>
          <select id="mk-un" class="ref-select" aria-label="Filter by UN agreement">
            <option value="">Any UN status</option>
            <option value="1958"${params.get("un") === "1958" ? " selected" : ""}>UN 1958 Agreement party</option>
            <option value="1998"${params.get("un") === "1998" ? " selected" : ""}>UN 1998 Agreement party</option>
            <option value="none"${params.get("un") === "none" ? " selected" : ""}>Neither (verified)</option>
          </select>
        </div>
        <details class="regime-legend"><summary>What the regime labels mean</summary>
          <dl>${Object.entries(regimes).map(([k, v]) => `<div><dt><span class="badge regime regime-${esc(k)}">${esc(v)}</span></dt><dd>${esc((K.markets.regime_descriptions || {})[k] || "")}</dd></div>`).join("")}</dl>
        </details>
        <div id="mk-list"></div>
      </div>`;
    const q = root.querySelector("#mk-q");
    const regimeSel = root.querySelector("#mk-regime");
    const unSel = root.querySelector("#mk-un");
    const update = () => {
      const p = new URLSearchParams({ view: "markets" });
      if (q.value.trim()) p.set("q", q.value.trim());
      if (regimeSel.value) p.set("regime", regimeSel.value);
      if (unSel.value) p.set("un", unSel.value);
      replaceParams(p);
      renderMarketList(q.value.trim().toLowerCase(), regimeSel.value, unSel.value);
    };
    q.addEventListener("input", update);
    regimeSel.addEventListener("change", update);
    unSel.addEventListener("change", update);
    renderMarketList((params.get("q") || "").toLowerCase(), params.get("regime") || "", params.get("un") || "");
  }

  function renderMarketList(q, regime, un) {
    const list = K.markets.markets.filter((m) =>
      (!q || marketHaystack(m).includes(q)) &&
      (!regime || m.regime === regime) &&
      (!un || (un === "1958" && m.un_1958 === true) || (un === "1998" && m.un_1998 === true) ||
        (un === "none" && m.un_1958 === false && m.un_1998 === false))
    );
    const groups = new Map();
    list.forEach((m) => { if (!groups.has(m.group)) groups.set(m.group, []); groups.get(m.group).push(m); });
    const html = K.markets.groups.filter((g) => groups.has(g)).map((g) => `
      <section class="mk-group">
        <h2 class="mk-group-head">${esc(g)} <span class="mk-group-count">${groups.get(g).length}</span></h2>
        <div class="mk-grid">${groups.get(g).map(marketCard).join("")}</div>
      </section>`).join("");
    root.querySelector("#mk-list").innerHTML = html || `<div class="empty-state">No market matches. Try a country name, an authority (e.g. NHTSA, MIIT, SASO) or clear the filters.</div>`;
  }

  // "Caribbean (Dominican Republic, Jamaica, …)" → ["Caribbean", "Dominican Republic, Jamaica, …"]
  function splitName(name) {
    const match = /^(.*?) \((.*)\)$/.exec(String(name || ""));
    return match ? [match[1], match[2]] : [String(name || ""), ""];
  }

  function marketCard(m) {
    const n = recordCountFor(m);
    const [title, sub] = splitName(m.name);
    const members = (m.members || []).length ? `<span>${m.members.length} countries</span>` : "";
    return `<a class="mk-card" href="?view=market&code=${encodeURIComponent(m.code)}" data-nav-href="view=market&code=${esc(encodeURIComponent(m.code))}">
      <span class="mk-card-head"><span class="mk-name">${esc(title)}</span>${regimeBadge(m)}</span>
      ${sub ? `<span class="mk-sub">${esc(sub)}</span>` : ""}
      <span class="mk-basis">${esc(m.basis)}</span>
      <span class="mk-meta"><span>${esc(m.drive)}</span>${unBadge("1958", m.un_1958)}${unBadge("1998", m.un_1998)}${members}${n ? `<span>${n} regulations in repo</span>` : ""}<span class="conf-dot conf-${esc(m.confidence)}" title="${esc(m.confidence)} confidence"></span></span>
    </a>`;
  }

  // ── Market profile ───────────────────────────────────────────────────
  function listSection(title, items, ordered) {
    if (!items || !items.length) return "";
    const tag = ordered ? "ol" : "ul";
    return `<section class="mp-section"><h2>${esc(title)}</h2><${tag}>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</${tag}></section>`;
  }

  function renderMarket(params) {
    const code = params.get("code");
    const m = K.marketByCode.get(code);
    if (!m) {
      root.innerHTML = `<div class="ref-wrap"><div class="empty-state">Unknown market "${esc(code)}". ${navLink("view=markets", "See all markets →")}</div></div>`;
      return;
    }
    setTitle(m.name);
    const [titleMain, titleSub] = splitName(m.name);
    const back = `Back to ${titleMain}`;
    const n = recordCountFor(m);
    const regionParams = (m.regions || []).map((r) => `region=${encodeURIComponent(r)}`).join("&");
    const authorities = (m.authorities || []).map((a) => `<li><strong>${a.url ? `<a href="${esc(a.url)}" rel="noopener noreferrer" target="_blank">${esc(a.name)} ↗</a>` : esc(a.name)}</strong>${a.scope ? `<span> — ${esc(a.scope)}</span>` : ""}</li>`).join("");
    const mapping = columnForMarket(m.code);
    root.innerHTML = `
      <div class="ref-wrap">
        <nav class="ref-crumbs">${navLink("view=markets", "Markets")} <span aria-hidden="true">›</span> ${esc(m.group)}</nav>
        <header class="ref-head mp-head">
          <h1 class="ref-title">${esc(titleMain)}</h1>
          ${titleSub ? `<p class="mp-sub">${esc(titleSub)}</p>` : ""}
          <div class="mp-badges">${regimeBadge(m)}<span class="badge">${esc(m.drive === "mixed" ? "LHD / RHD varies" : m.drive)}</span>${unBadge("1958", m.un_1958)}${unBadge("1998", m.un_1998)}${confBadge(m.confidence)}</div>
          <p class="mp-basis"><span class="mp-label">Technical basis</span>${esc(m.basis)}</p>
          <div class="mp-actions">
            ${n ? navLink(regionParams, `Browse ${n} regulations →`, "btn-primary") : ""}
            ${navLink(`view=planner&m=${encodeURIComponent(m.code)}`, "Open in launch planner", "btn-ghost")}
            ${mapping ? navLink(`view=crosswalk&cols=${encodeURIComponent(mapping.col.key)}`, `${esc(mapping.col.short)} in crosswalk`, "btn-ghost") : ""}
          </div>
          ${caveat()}
        </header>
        ${(m.members || []).length ? `<section class="mp-section"><h2>Countries covered</h2><p class="mp-members">${m.members.map(esc).join(" · ")}</p></section>` : ""}
        <div class="mp-cols">
          <div>
            <section class="mp-section"><h2>Authorities</h2><ul class="mp-auth">${authorities}</ul></section>
            ${listSection("Approval process", m.process, true)}
            ${listSection("Marks, labels & certificates", m.marks)}
          </div>
          <div>
            ${listSection("Accepted foreign approvals / evidence", m.accepts.length ? m.accepts : ["None — national certification required"])}
            <section class="mp-section"><h2>Emissions & energy</h2><p>${esc(m.emissions)}</p></section>
            <section class="mp-section"><h2>Language</h2><p>${esc(m.language)}</p></section>
            ${listSection("Watch list — upcoming changes", m.watch)}
            ${listSection("Notes", m.notes)}
          </div>
        </div>
        ${(m.records || []).length ? `<section class="mp-section"><h2>Key instruments in this repository</h2>${recordChips(m.records, back)}</section>` : ""}
        ${mapping ? marketRequirementMap(m, mapping, back) : `<section class="mp-section"><h2>Requirement map</h2><p class="muted">No crosswalk column represents this market yet — use the accepted-approvals list above to decide which regime's evidence applies.</p></section>`}
      </div>`;
  }

  function marketRequirementMap(m, mapping, back) {
    const via = mapping.via
      ? `<p class="muted">${esc(m.name)} has no dedicated column; it applies <strong>${esc(mapping.via)}</strong> as its technical basis, so the ${esc(mapping.col.label)} column is shown. Check national deviations in the notes above.</p>`
      : "";
    const rows = K.crosswalk.groups.map((g) => {
      const topics = K.crosswalk.topics.filter((t) => t.group === g);
      const body = topics.map((t) => {
        const cell = t.cells[mapping.col.key];
        return `<tr><th scope="row">${navLink(`view=topic&t=${encodeURIComponent(t.id)}`, esc(t.title))}</th>
          <td>${cell ? `${esc(cell.cite)} ${statusBadge(cell.status)}${cell.note ? `<div class="cw-note-text">${esc(cell.note)}</div>` : ""}${recordChips(cell.records, back, 4)}` : `<span class="muted">Not mapped</span>`}</td></tr>`;
      }).join("");
      return `<tr class="cw-group-row"><th colspan="2">${esc(g)}</th></tr>${body}`;
    }).join("");
    return `<section class="mp-section"><h2>Requirement map — ${esc(mapping.col.label)}</h2>${via}
      <div class="table-scroll"><table class="cw-table mp-map"><thead><tr><th>Requirement</th><th>${esc(mapping.col.short)}</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
  }

  // ── Crosswalk matrix ─────────────────────────────────────────────────
  function selectedCols(params) {
    const raw = (params.get("cols") || "").split(",").filter((k) => K.colByKey.has(k));
    return raw.length ? raw : K.crosswalk.columns.map((c) => c.key);
  }

  function renderCrosswalk(params) {
    setTitle("Requirement crosswalk");
    const cols = selectedCols(params);
    root.innerHTML = `
      <div class="ref-wrap ref-wide">
        <header class="ref-head">
          <p class="ref-eyebrow">Requirement crosswalk</p>
          <h1 class="ref-title">What is this requirement called in each market?</h1>
          <p class="ref-lede">${K.crosswalk.topics.length} requirement topics × ${K.crosswalk.columns.length} regulatory regimes. Each cell gives the governing citation; red chips open the regulation text in this repository. An empty cell means <em>not mapped yet</em>, not "no requirement".</p>
          ${caveat(`Reviewed ${esc(K.crosswalk.reviewed)}. `)}
        </header>
        <div class="ref-controls">
          <input type="search" id="cw-q" class="ref-input" placeholder="Filter topics or citations (e.g. side impact, R94, FMVSS 305a, ISOFIX)…" aria-label="Filter crosswalk" value="${esc(params.get("q") || "")}">
          <select id="cw-group" class="ref-select" aria-label="Filter by group">
            <option value="">All groups</option>
            ${K.crosswalk.groups.map((g) => `<option${params.get("group") === g ? " selected" : ""}>${esc(g)}</option>`).join("")}
          </select>
        </div>
        <fieldset class="col-toggles"><legend>Columns</legend>
          ${K.crosswalk.columns.map((c) => `<label class="col-toggle"><input type="checkbox" value="${esc(c.key)}"${cols.includes(c.key) ? " checked" : ""}><span>${esc(c.short)}</span></label>`).join("")}
          <button type="button" class="link-btn" id="cw-all">All</button>
        </fieldset>
        <div id="cw-table"></div>
      </div>`;
    const q = root.querySelector("#cw-q");
    const grp = root.querySelector("#cw-group");
    const boxes = Array.from(root.querySelectorAll(".col-toggles input"));
    const update = () => {
      const chosen = boxes.filter((b) => b.checked).map((b) => b.value);
      const p = new URLSearchParams({ view: "crosswalk" });
      if (q.value.trim()) p.set("q", q.value.trim());
      if (grp.value) p.set("group", grp.value);
      if (chosen.length && chosen.length < boxes.length) p.set("cols", chosen.join(","));
      replaceParams(p);
      renderCrosswalkTable(q.value.trim().toLowerCase(), grp.value, chosen.length ? chosen : boxes.map((b) => b.value));
    };
    q.addEventListener("input", update);
    grp.addEventListener("change", update);
    boxes.forEach((b) => b.addEventListener("change", update));
    root.querySelector("#cw-all").addEventListener("click", () => { boxes.forEach((b) => { b.checked = true; }); update(); });
    renderCrosswalkTable((params.get("q") || "").toLowerCase(), params.get("group") || "", cols);
  }

  function topicHaystack(t) {
    return [t.title, t.description, t.group, t.gtr || "", ...Object.values(t.cells).map((c) => `${c.cite} ${c.note || ""}`)].join(" ").toLowerCase();
  }

  function cellHtml(cell, back, compact) {
    if (!cell) return `<span class="muted">—</span>`;
    const note = cell.note ? (compact
      ? ` <span class="cw-note" tabindex="0" data-tooltip="${esc(cell.note)}" aria-label="Note: ${esc(cell.note)}">ⓘ</span>`
      : `<div class="cw-note-text">${esc(cell.note)}</div>`) : "";
    return `<div class="cw-cell${cell.status === "none" ? " is-none" : ""}"><span class="cw-cite">${esc(cell.cite)}</span>${note} ${statusBadge(cell.status)}${recordChips(cell.records, back, compact ? 3 : undefined)}</div>`;
  }

  function renderCrosswalkTable(q, group, cols) {
    const columns = cols.map((k) => K.colByKey.get(k));
    const topics = K.crosswalk.topics.filter((t) => (!group || t.group === group) && (!q || topicHaystack(t).includes(q)));
    if (!topics.length) {
      root.querySelector("#cw-table").innerHTML = `<div class="empty-state">No topic matches “${esc(q)}”.</div>`;
      return;
    }
    const back = "Back to crosswalk";
    const rows = K.crosswalk.groups.map((g) => {
      const ts = topics.filter((t) => t.group === g);
      if (!ts.length) return "";
      return `<tr class="cw-group-row"><th colspan="${columns.length + 1}">${esc(g)}</th></tr>` + ts.map((t) => `
        <tr>
          <th scope="row" class="cw-topic">${navLink(`view=topic&t=${encodeURIComponent(t.id)}`, esc(t.title))}${t.gtr ? `<span class="badge gtr">${esc(t.gtr)}</span>` : ""}${t.powertrains.length < 5 ? `<span class="badge pt">${esc(t.powertrains.join("/"))}</span>` : ""}</th>
          ${columns.map((c) => `<td>${cellHtml(t.cells[c.key], back, true)}</td>`).join("")}
        </tr>`).join("");
    }).join("");
    root.querySelector("#cw-table").innerHTML = `
      <p class="muted cw-count">${topics.length} topics · ${columns.length} columns</p>
      <div class="table-scroll"><table class="cw-table">
        <thead><tr><th scope="col">Requirement</th>${columns.map((c) => `<th scope="col"><span title="${esc(c.label)}">${esc(c.short)}</span></th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
      </table></div>`;
  }

  // ── Topic detail ─────────────────────────────────────────────────────
  function renderTopic(params) {
    const t = K.topicById.get(params.get("t"));
    if (!t) {
      root.innerHTML = `<div class="ref-wrap"><div class="empty-state">Unknown topic. ${navLink("view=crosswalk", "Back to the crosswalk →")}</div></div>`;
      return;
    }
    setTitle(t.title);
    const back = `Back to ${t.title}`;
    const viaUn = K.markets.markets.filter((m) => { const c = columnForMarket(m.code); return c && c.via === "UN R"; }).map((m) => m.name);
    root.innerHTML = `
      <div class="ref-wrap">
        <nav class="ref-crumbs">${navLink("view=crosswalk", "Crosswalk")} <span aria-hidden="true">›</span> ${navLink(`view=crosswalk&group=${encodeURIComponent(t.group)}`, esc(t.group))}</nav>
        <header class="ref-head">
          <h1 class="ref-title">${esc(t.title)}</h1>
          <p class="ref-lede">${esc(t.description)}</p>
          <div class="mp-badges">${t.gtr ? `<span class="badge gtr">UN ${esc(t.gtr)}</span>` : ""}<span class="badge pt">${t.powertrains.length === 5 ? "All powertrains" : esc(t.powertrains.map((p) => PT_LABELS[p]).join(", "))}</span></div>
          ${caveat()}
        </header>
        <div class="topic-list">
          ${K.crosswalk.columns.map((c) => {
            const cell = t.cells[c.key];
            const m = K.marketByCode.get(c.market);
            return `<section class="topic-row${cell ? "" : " is-empty"}">
              <h2>${m ? navLink(`view=market&code=${encodeURIComponent(m.code)}`, esc(c.label)) : esc(c.label)}</h2>
              ${cell ? cellHtml(cell, back, false) : `<span class="muted">Not mapped yet — see the market profile.</span>`}
            </section>`;
          }).join("")}
        </div>
        <p class="muted topic-foot">Markets that apply UN Regulations as their basis (${esc(viaUn.join(", "))}) generally accept the <strong>UN R</strong> column — check each profile for national deviations.</p>
        <p>${navLink(`view=planner&m=US,EU,CN,JP`, "Plan a launch with this topic →")}</p>
      </div>`;
  }

  // ── Launch planner ───────────────────────────────────────────────────
  function plannerState(params) {
    const codes = (params.get("m") || "").split(",").filter((c) => K.marketByCode.has(c));
    const pt = Object.keys(PT_LABELS).includes(params.get("pt")) ? params.get("pt") : "ICE";
    return { codes, pt };
  }

  function plannerParams(state) {
    const p = new URLSearchParams({ view: "planner" });
    if (state.codes.length) p.set("m", state.codes.join(","));
    p.set("pt", state.pt);
    return p;
  }

  function renderPlanner(params) {
    setTitle("Launch planner");
    const state = plannerState(params);
    const groups = K.markets.groups.map((g) => {
      const ms = K.markets.markets.filter((m) => m.group === g);
      if (!ms.length) return "";
      return `<div class="pl-group"><p class="pl-group-head">${esc(g)}</p>${ms.map((m) =>
        `<label class="pl-market"><input type="checkbox" value="${esc(m.code)}"${state.codes.includes(m.code) ? " checked" : ""}><span>${esc(m.name)}</span></label>`).join("")}</div>`;
    }).join("");
    root.innerHTML = `
      <div class="ref-wrap ref-wide">
        <header class="ref-head">
          <p class="ref-eyebrow">Launch planner</p>
          <h1 class="ref-title">What do I need to certify this vehicle in these markets?</h1>
          <p class="ref-lede">Choose target markets and a powertrain. You get each market's approval route and a requirement checklist mapped to the governing regulation in each market — export it to CSV for your compliance matrix or DVP&amp;R.</p>
          ${caveat()}
        </header>
        <div class="pl-layout">
          <aside class="pl-picker" aria-label="Plan inputs">
            <fieldset class="pl-pt"><legend>Powertrain</legend>
              ${Object.entries(PT_LABELS).map(([k, v]) => `<label class="seg"><input type="radio" name="pt" value="${k}"${state.pt === k ? " checked" : ""}><span>${esc(v)}</span></label>`).join("")}
            </fieldset>
            <fieldset><legend>Target markets</legend>
              <div class="pl-presets">${PLANNER_PRESETS.map((p, i) => `<button type="button" class="link-btn" data-preset="${i}">${esc(p.label)}</button>`).join("")}<button type="button" class="link-btn" data-preset="clear">Clear</button></div>
              <div class="pl-markets">${groups}</div>
            </fieldset>
          </aside>
          <div class="pl-output" id="pl-output"></div>
        </div>
      </div>`;
    const sync = () => {
      const s = {
        codes: Array.from(root.querySelectorAll(".pl-market input:checked")).map((b) => b.value),
        pt: (root.querySelector(".pl-pt input:checked") || {}).value || "ICE",
      };
      replaceParams(plannerParams(s));
      renderPlannerOutput(s);
    };
    root.querySelectorAll(".pl-market input, .pl-pt input").forEach((el) => el.addEventListener("change", sync));
    root.querySelectorAll("[data-preset]").forEach((btn) => btn.addEventListener("click", () => {
      const preset = btn.dataset.preset === "clear" ? [] : PLANNER_PRESETS[Number(btn.dataset.preset)].codes;
      root.querySelectorAll(".pl-market input").forEach((b) => { b.checked = preset.includes(b.value); });
      sync();
    }));
    renderPlannerOutput(state);
  }

  function plannerRows(state) {
    const topics = K.crosswalk.topics.filter((t) => t.powertrains.includes(state.pt));
    const markets = state.codes.map((c) => K.marketByCode.get(c));
    return { topics, markets, maps: markets.map((m) => columnForMarket(m.code)) };
  }

  function renderPlannerOutput(state) {
    const out = root.querySelector("#pl-output");
    if (!state.codes.length) {
      out.innerHTML = `<div class="empty-state pl-empty">Select one or more target markets (or a preset) to build the plan.</div>`;
      return;
    }
    const { topics, markets, maps } = plannerRows(state);
    const back = "Back to launch planner";
    let mapped = 0, linked = 0;
    topics.forEach((t) => maps.forEach((mp) => {
      const cell = mp && t.cells[mp.col.key];
      if (cell) { mapped += 1; if ((cell.records || []).length) linked += 1; }
    }));
    const routeCards = markets.map((m) => `
      <article class="pl-route">
        <h3>${navLink(`view=market&code=${encodeURIComponent(m.code)}`, esc(m.name))}</h3>
        <div class="mp-badges">${regimeBadge(m)}<span class="badge">${esc(m.drive)}</span><span class="conf-dot conf-${esc(m.confidence)}" title="${esc(m.confidence)} confidence"></span></div>
        <p><span class="mp-label">Authority</span>${esc((m.authorities || []).map((a) => a.name).slice(0, 3).join("; "))}</p>
        <p><span class="mp-label">Basis</span>${esc(m.basis)}</p>
        ${(m.marks || []).length ? `<p><span class="mp-label">Key marks</span>${esc(m.marks.slice(0, 2).join(" · "))}${m.marks.length > 2 ? " …" : ""}</p>` : ""}
        <p><span class="mp-label">Emissions</span>${esc(m.emissions)}</p>
        <p><span class="mp-label">Language</span>${esc(m.language)}</p>
        ${(m.watch || []).length ? `<p class="pl-watch"><span class="mp-label">Watch</span>${esc(m.watch[0])}${m.watch.length > 1 ? ` (+${m.watch.length - 1} more)` : ""}</p>` : ""}
      </article>`).join("");
    const head = markets.map((m, i) => `<th scope="col">${esc(m.name)}${maps[i] ? `<span class="pl-basis">${esc(maps[i].via ? `via ${maps[i].via}` : maps[i].col.short)}</span>` : `<span class="pl-basis">profile only</span>`}</th>`).join("");
    const body = K.crosswalk.groups.map((g) => {
      const ts = topics.filter((t) => t.group === g);
      if (!ts.length) return "";
      return `<tr class="cw-group-row"><th colspan="${markets.length + 1}">${esc(g)}</th></tr>` + ts.map((t) => `<tr>
        <th scope="row" class="cw-topic">${navLink(`view=topic&t=${encodeURIComponent(t.id)}`, esc(t.title))}</th>
        ${maps.map((mp) => `<td>${mp ? cellHtml(t.cells[mp.col.key], back, true) : `<span class="muted">See profile</span>`}</td>`).join("")}
      </tr>`).join("");
    }).join("");
    out.innerHTML = `
      <div class="pl-summary">
        <p><strong>${markets.length}</strong> markets · <strong>${topics.length}</strong> requirement topics for ${esc(PT_LABELS[state.pt])} · <strong>${mapped}</strong> mapped cells · <strong>${linked}</strong> with regulation text in the repository</p>
        <div class="pl-actions">
          <button type="button" class="btn-primary" id="pl-csv">Export CSV</button>
          <button type="button" class="btn-ghost" id="pl-print">Print</button>
        </div>
      </div>
      <h2 class="pl-h">Approval routes</h2>
      <div class="pl-routes">${routeCards}</div>
      <h2 class="pl-h">Requirement checklist</h2>
      <p class="muted">“via UN R” columns show the UN Regulation a market applies or accepts; “See profile” means the market has no mapped basis — read its profile for the national standards.</p>
      <div class="table-scroll"><table class="cw-table pl-table"><thead><tr><th scope="col">Requirement</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
    out.querySelector("#pl-csv").addEventListener("click", () => downloadCsv(state));
    out.querySelector("#pl-print").addEventListener("click", () => window.print());
  }

  function csvCell(value) {
    const s = String(value ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }

  function plannerCsv(state) {
    const { topics, markets, maps } = plannerRows(state);
    const lines = [["Market", "Regime", "Basis column", "Requirement group", "Requirement", "Citation", "Status", "Note", "Repository records", "Source URLs"].map(csvCell).join(",")];
    markets.forEach((m, i) => {
      const mp = maps[i];
      topics.forEach((t) => {
        const cell = mp ? t.cells[mp.col.key] : null;
        const recs = cell ? (cell.records || []).map((id) => app().record(id)).filter(Boolean) : [];
        lines.push([
          m.name, m.regime_label, mp ? (mp.via ? `via ${mp.via}` : mp.col.short) : "profile only",
          t.group, t.title,
          cell ? cell.cite : (mp ? "Not mapped" : "See market profile"),
          cell ? (STATUS_LABELS[cell.status] || "Mandatory") : "",
          cell && cell.note ? cell.note : "",
          recs.map((r) => r.citation || r.id).join("; "),
          recs.map((r) => r.source_url).filter(Boolean).join(" "),
        ].map(csvCell).join(","));
      });
    });
    return lines.join("\r\n") + "\r\n";
  }

  function downloadCsv(state) {
    const blob = new Blob(["﻿" + plannerCsv(state)], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `launch-plan-${state.codes.join("-").toLowerCase()}-${state.pt.toLowerCase()}.csv`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  // ── Glossary ─────────────────────────────────────────────────────────
  function renderGlossary(params) {
    setTitle("Glossary");
    root.innerHTML = `
      <div class="ref-wrap">
        <header class="ref-head">
          <p class="ref-eyebrow">Glossary</p>
          <h1 class="ref-title">Certification &amp; homologation terms</h1>
          <p class="ref-lede">${K.glossary.length} terms used across approval regimes, with links to the markets that use them and the underlying instruments.</p>
        </header>
        <div class="ref-controls"><input type="search" id="gl-q" class="ref-input" placeholder="Filter terms (e.g. CoP, RAV, CSMS)…" aria-label="Filter glossary" value="${esc(params.get("q") || "")}"></div>
        <dl class="glossary" id="gl-list"></dl>
      </div>`;
    const q = root.querySelector("#gl-q");
    const update = () => {
      const p = new URLSearchParams({ view: "glossary" });
      if (q.value.trim()) p.set("q", q.value.trim());
      replaceParams(p);
      renderGlossaryList(q.value.trim().toLowerCase());
    };
    q.addEventListener("input", update);
    renderGlossaryList((params.get("q") || "").toLowerCase());
  }

  function renderGlossaryList(q) {
    const terms = K.glossary.filter((t) => !q || [t.term, ...(t.aka || []), t.definition].join(" ").toLowerCase().includes(q));
    root.querySelector("#gl-list").innerHTML = terms.map((t) => `
      <div class="gl-item" id="term-${esc(t.term.toLowerCase().replace(/[^a-z0-9]+/g, "-"))}">
        <dt>${esc(t.term)}${(t.aka || []).length ? `<span class="gl-aka">${esc(t.aka.join(" · "))}</span>` : ""}</dt>
        <dd>
          <p>${esc(t.definition)}</p>
          ${(t.markets || []).length ? `<p class="gl-links">${t.markets.map((c) => { const m = K.marketByCode.get(c); return m ? navLink(`view=market&code=${encodeURIComponent(c)}`, esc(m.name), "mk-chip") : ""; }).join("")}</p>` : ""}
          ${recordChips(t.records, "Back to glossary")}
        </dd>
      </div>`).join("") || `<div class="empty-state">No term matches.</div>`;
  }

  // ── Search hints (shown above workspace results) ─────────────────────
  function hints(query) {
    if (!K) return "";
    const q = String(query || "").trim();
    if (q.length < 2) return "";
    const lower = q.toLowerCase();
    const safe = lower.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const word = new RegExp(`(^|[^a-z0-9])${safe}`, "i");
    const markets = K.markets.markets.filter((m) => {
      if (m.code.toLowerCase() === lower) return true;
      if (q.length < 3) return false;
      return [m.name, ...(m.aliases || []), ...(m.members || [])].some((s) => word.test(s));
    }).slice(0, 3);
    const topics = q.length < 3 ? [] : K.crosswalk.topics.filter((t) =>
      word.test(t.title) || Object.values(t.cells).some((c) => word.test(c.cite))
    ).slice(0, 4);
    const terms = q.length < 2 ? [] : K.glossary.filter((t) => t.term.toLowerCase() === lower || (t.aka || []).some((a) => a.toLowerCase() === lower)).slice(0, 2);
    if (!markets.length && !topics.length && !terms.length) return "";
    const chips = [
      ...markets.map((m) => navLink(`view=market&code=${encodeURIComponent(m.code)}`, `<span class="hint-kind">Market</span>${esc(m.name)}`, "hint-chip")),
      ...topics.map((t) => navLink(`view=topic&t=${encodeURIComponent(t.id)}`, `<span class="hint-kind">Crosswalk</span>${esc(t.title)}`, "hint-chip")),
      ...terms.map((t) => navLink(`view=glossary&q=${encodeURIComponent(t.term)}`, `<span class="hint-kind">Term</span>${esc(t.term)}`, "hint-chip")),
    ];
    return `<span class="hint-label">Reference:</span>${chips.join("")}`;
  }

  // ── dispatch & delegated clicks ──────────────────────────────────────
  const RENDERERS = {
    markets: renderMarkets,
    market: renderMarket,
    crosswalk: renderCrosswalk,
    topic: renderTopic,
    planner: renderPlanner,
    glossary: renderGlossary,
  };

  function render(view, params) {
    if (!K) {
      root.innerHTML = `<div class="ref-wrap"><p class="muted">Loading reference data…</p></div>`;
      load().then(() => render(view, params)).catch(() => {
        root.innerHTML = `<div class="ref-wrap"><div class="empty-state">Reference data failed to load.</div></div>`;
      });
      return;
    }
    (RENDERERS[view] || renderMarkets)(params);
  }

  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    const rec = event.target.closest("[data-record]");
    if (rec && (root.contains(rec))) {
      event.preventDefault();
      app().openRecord(rec.dataset.record, rec.dataset.back);
      return;
    }
    const nav = event.target.closest("[data-nav-href], [data-nav-tool]");
    if (nav) {
      event.preventDefault();
      const search = nav.dataset.navHref || `view=${nav.dataset.navTool}`;
      app().navigate(search);
    }
  });

  window.RefViews = { load, render, hints, plannerCsv, columnForMarket: (c) => (K ? columnForMarket(c) : null) };
})();
