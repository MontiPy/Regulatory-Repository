    let REGS = [];
    let TAXONOMY = {};
    let recordById = new Map();
    let UN_INDEX = {};
    const bodyCache = new Map();      // id -> body_html (lazy)
    let searchEngine = null;          // MiniSearch instance (lazy)
    let searchReady = false;
    let searchDocsById = new Map();   // id -> full search text (for body-match snippets)

    const PAGE_SIZE = 50;
    const FILTERS = [
      { key: "region",             label: "Region",           taxonomyKey: "regions",              tooltip: "The jurisdiction that issued the regulation — US, EU, JP, KR, AU, CA, ECE (UN), BR, GCC, CN, TW, or IN." },
      { key: "systems",            label: "System",           taxonomyKey: "systems",              tooltip: "The functional vehicle system the regulation governs, e.g. braking, ADAS, or emissions. Higher-level grouping than Commodity." },
      { key: "commodities",        label: "Commodity",        taxonomyKey: "commodities",          tooltip: "The specific physical part or component targeted, e.g. airbags, tires, or charging inlet. More granular than System — a single regulation may cover several commodities." },
      { key: "vehicle_categories", label: "Vehicle Category", taxonomyKey: "vehicle_categories",   tooltip: "The type of vehicle the regulation applies to." },
      { key: "status",             label: "Status",           taxonomyKey: "statuses",             tooltip: "Where the regulation stands in its lifecycle: Active (currently in force), Proposed (open for comment), Withdrawn (removed without replacement), or Superseded (replaced by a newer regulation)." },
      { key: "tagging_status",     label: "Tagging Status",   taxonomyKey: "tagging_statuses",     tooltip: "Whether the regulation has been classified with metadata (systems, commodities, vehicle categories). Untagged = not yet processed; LLM-tagged = classified automatically." },
      { key: "translation_status", label: "Translation",      taxonomyKey: "translation_statuses", tooltip: "Whether the regulation text has been translated to English. Untranslated = original language only." },
    ];
    const PRIMARY_FILTERS = new Set(["region", "systems", "commodities"]);
    const FACET_MORE_LABELS = {
      region: "regions", systems: "systems", commodities: "commodities",
      vehicle_categories: "vehicle categories", status: "statuses",
      tagging_status: "tagging statuses", translation_status: "translation statuses",
    };

    const searchInput   = document.querySelector("#search");
    const filtersForm   = document.querySelector("#filters-form");
    const cards         = document.querySelector("#cards");
    const resultCount   = document.querySelector("#result-count");
    const loadMore      = document.querySelector("#load-more");
    const clearFilters  = document.querySelector("#clear-filters");
    const copyLink      = document.querySelector("#copy-link");
    const availBoxes    = Array.from(document.querySelectorAll("[data-avail]"));
    const homeView      = document.querySelector("#home");
    const workspaceEls  = [document.querySelector(".layout")];
    const homeLink      = document.querySelector("#home-link");
    const homeSearch    = document.querySelector("#home-search");
    let openReaderId    = null;
    let readerOrigin    = null;
    let visibleLimit    = PAGE_SIZE;
    let urlTimer        = null;

    const homeSort    = { systems: "az", commodities: "az", region: "count" };
    const homeShowAll = { systems: false, commodities: false, region: false };
    const HOME_TOP_N  = 14;

    function marketTileLabel(region) {
      const meta = (TAXONOMY.region_series || {})[region];
      if (meta && meta.series) return `${meta.series} (${meta.name || region})`;
      if (meta && meta.name) return meta.name;
      return region;
    }

    // Corpus-wide value counts (over ALL records, independent of filters) used to
    // decide which facet options/sections are worth rendering.
    let CORPUS_COUNTS = {};
    function rebuildCorpusCounts() {
      const counts = {};
      FILTERS.forEach((f) => { counts[f.key] = {}; });
      REGS.forEach((r) => {
        FILTERS.forEach((f) => {
          const raw = r[f.key];
          const vals = Array.isArray(raw) ? raw : (raw != null && raw !== "" ? [raw] : []);
          vals.forEach((v) => { counts[f.key][v] = (counts[f.key][v] || 0) + 1; });
        });
      });
      CORPUS_COUNTS = counts;
    }

    // Content-availability category for the header "Show" bar.
    //   full    — full regulation text from a live source
    //   paywall — requires purchase / institutional access
    //   noconn  — catalog stub, no live connector yet
    const AVAIL_CATEGORIES = ["full", "paywall", "noconn"];
    function availabilityCategory(record) {
      if (record.paywall === true) return "paywall";
      if (record.source_api === "spreadsheet") return "noconn";
      return "full";
    }
    function selectedAvailability() {
      return new Set(availBoxes.filter((b) => b.checked).map((b) => b.dataset.avail));
    }

    const DISPLAY_LABELS = { "in-force": "Active", "llm-tagged": "LLM-tagged" };
    function displayLabel(value) {
      const str = String(value ?? "");
      if (DISPLAY_LABELS[str] !== undefined) return DISPLAY_LABELS[str];
      return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function highlight(text, query) {
      const escaped = escapeHtml(text);
      if (!query || query.trim().length < 2) return escaped;
      const safe = query.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      try {
        return escaped.replace(new RegExp(`(${safe})`, "gi"), "<mark>$1</mark>");
      } catch {
        return escaped;
      }
    }

    function slug(value) {
      return String(value ?? "").replace(/[^a-zA-Z0-9_-]/g, "-");
    }

    function statusClass(status) {
      return `status-${String(status || "").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    }

    function normalize(value) {
      return String(value ?? "").toLowerCase();
    }

    function matchesFacet(values, selected) {
      if (!selected || selected.size === 0) return true;
      return values.some((v) => selected.has(v));
    }

    function matchesText(r, query) {
      const q = normalize(query).trim();
      if (!q) return true;
      const base = [
        r.title, r.citation,
        (r.aliases || []).join(" "),
        r.summary_text,
        (r.un_equivalent || []).join(" "),
        (r.tags || []).join(" "),
        (r.open_tags || []).join(" "),
      ].join(" ");
      if (normalize(base).includes(q)) return true;
      if (searchReady && q.length >= 3) return searchHitIds().has(r.id);
      return false;
    }

    let _lastQuery = null, _lastHits = new Set();
    function searchHitIds() {
      const q = searchInput.value.trim();
      if (q === _lastQuery) return _lastHits;
      _lastQuery = q;
      _lastHits = new Set(searchEngine.search(q, { prefix: true }).map((h) => h.id));
      return _lastHits;
    }

    function loadSearch() {
      if (searchEngine) return;
      fetch("data/search-text.json")
        .then((r) => r.json())
        .then((docs) => {
          searchEngine = new MiniSearch({ fields: ["text"], storeFields: ["id"] });
          searchEngine.addAll(docs);
          searchReady = true;
          searchDocsById = new Map(docs.map((doc) => [doc.id, doc.text || ""]));
          if (searchInput.value.trim()) render();
        })
        .catch((err) => { console.warn("search index unavailable:", err); });
    }

    function readSelections() {
      const sel = {};
      FILTERS.forEach((f) => {
        sel[f.key] = new Set(
          Array.from(filtersForm.querySelectorAll(`input[name="${f.key}"]:checked`)).map((el) => el.value)
        );
      });
      return sel;
    }

    function getVisibleRecords() {
      const q = searchInput.value;
      const sel = readSelections();
      const avail = selectedAvailability();
      return REGS.filter((r) =>
        avail.has(availabilityCategory(r)) &&
        matchesText(r, q) &&
        matchesFacet([r.region], sel.region) &&
        matchesFacet([r.status], sel.status) &&
        matchesFacet([r.tagging_status], sel.tagging_status) &&
        matchesFacet([r.translation_status], sel.translation_status) &&
        matchesFacet(r.vehicle_categories || [], sel.vehicle_categories) &&
        matchesFacet(r.systems || [], sel.systems) &&
        matchesFacet(r.commodities || [], sel.commodities)
      );
    }

    function updateClearButton() {
      const hasSearch  = searchInput.value.trim() !== "";
      const hasChecked = filtersForm.querySelectorAll("input:checked").length > 0;
      clearFilters.classList.toggle("hidden", !hasSearch && !hasChecked);
    }

    function updateFacetCounts(visible) {
      const counts = {};
      FILTERS.forEach((f) => { counts[f.key] = {}; });
      visible.forEach((r) => {
        FILTERS.forEach((f) => {
          const vals = Array.isArray(r[f.key]) ? r[f.key]
            : r[f.key] != null ? [r[f.key]] : [];
          vals.forEach((v) => { counts[f.key][v] = (counts[f.key][v] || 0) + 1; });
        });
      });
      filtersForm.querySelectorAll(".facet-count[data-facet]").forEach((el) => {
        const n = counts[el.dataset.facet]?.[el.dataset.value] || 0;
        el.textContent = n;
        const option = el.closest(".facet-option");
        const checked = option.querySelector("input")?.checked;
        // A checked option stays visible even at zero so it can be unchecked.
        option.classList.toggle("empty", n === 0 && !checked);
      });
      updateFacetCollapse();
    }

    function facetChips(label, values, chipClass) {
      if (!values || values.length === 0) return "";
      const cls = chipClass ? `chip ${chipClass}` : "chip";
      const chips = values.map((v) => `<span class="${cls}">${escapeHtml(v)}</span>`).join("");
      return `<div class="meta-item"><strong>${escapeHtml(label)}</strong><div class="chips">${chips}</div></div>`;
    }

    function relatedLinks(values) {
      if (!values || values.length === 0) return "";
      const links = values.map((id) => {
        const rec = recordById.get(id);
        if (!rec) return `<span class="chip">${escapeHtml(id)}</span>`;
        return `<a class="chip" href="?id=${encodeURIComponent(id)}" data-read="${escapeHtml(id)}">${escapeHtml(rec.title || id)}</a>`;
      }).join("");
      return `<div class="meta-item"><strong>Related</strong><div class="chips">${links}</div></div>`;
    }

    // Render UN R numbers as chips, linking to the ECE record when one exists.
    // `unverified` adds the AI treatment (dashed, tinted) + a verify note.
    function unChips(label, values, unverified) {
      if (!values || values.length === 0) return "";
      const cls = unverified ? "chip ai" : "chip";
      const chips = values.map((un) => {
        const targetId = UN_INDEX[un];
        if (targetId && recordById.has(targetId)) {
          const tip = unverified ? "AI-suggested — verify against source" : un;
          return `<a class="${cls}" href="?id=${encodeURIComponent(targetId)}" data-read="${escapeHtml(targetId)}" title="${escapeHtml(tip)}">${escapeHtml(un)}</a>`;
        }
        return `<span class="${cls}">${escapeHtml(un)}</span>`;
      }).join("");
      const note = unverified
        ? `<span class="ai-note">AI-suggested — verify against source</span>`
        : "";
      return `<div class="meta-item${unverified ? " ai" : ""}"><strong>${escapeHtml(label)}</strong>${note}<div class="chips">${chips}</div></div>`;
    }

    function stubBanner(record) {
      if (record.source_api !== "spreadsheet") return "";
      const srcLink = record.source_url
        ? ` <a href="${escapeHtml(record.source_url)}" rel="noopener noreferrer">Visit official source.</a>`
        : "";
      if (record.paywall) {
        return `<div class="stub-banner paywalled">
          <span class="stub-banner-icon">&#x1F512;</span>
          <span>Full text not available — this standard requires purchase or institutional access. Content below is derived from the reference repository.${srcLink}</span>
        </div>`;
      }
      return `<div class="stub-banner no-paywall">
        <span class="stub-banner-icon">&#x26A0;&#xFE0F;</span>
        <span>Full text not available — no live connector yet. Content below is derived from the reference repository.${srcLink}</span>
      </div>`;
    }

    function hostLabel(url) {
      try { return new URL(url).hostname.replace(/^www\./, ""); }
      catch { return url; }
    }

    function sourceLinkHtml(record) {
      if (!record.source_url) return "";
      return `<a href="${escapeHtml(record.source_url)}" rel="noopener noreferrer">${escapeHtml(hostLabel(record.source_url))} ↗</a>`;
    }

    function readerTrustHtml(record) {
      const chips = [];
      if (record.status) chips.push(`<span class="reader-trust-chip">${escapeHtml(displayLabel(record.status))}</span>`);
      if (record.citation) chips.push(`<span class="reader-trust-chip">${escapeHtml(record.citation)}</span>`);
      if (record.source_url) chips.push(`<span class="reader-trust-chip source">Source: ${sourceLinkHtml(record)}</span>`);
      if (record.last_pulled) chips.push(`<span class="reader-trust-chip">Pulled ${escapeHtml(record.last_pulled.slice(0, 10))}</span>`);
      if ((record.un_equivalent_ai || []).length) chips.push(`<span class="reader-trust-chip">AI equivalent needs verification</span>`);
      return chips.join("");
    }

    // Honest provenance: systems/commodities/vehicle categories come from the
    // automated tagging pass, so flag them as AI-classified (mirrors the
    // verified-vs-AI treatment already used for UN equivalents).
    function classificationNote(record) {
      const hasTags = (record.systems || []).length
        || (record.commodities || []).length
        || (record.vehicle_categories || []).length;
      if (!hasTags || record.tagging_status !== "llm-tagged") return "";
      return `<p class="meta-provenance">Systems, commodities &amp; vehicle categories are AI-classified — verify against the source text.</p>`;
    }

    function readerBodyHtml(record) {
      const sourceHtml = sourceLinkHtml(record);
      return `
        <div class="expanded">
          ${stubBanner(record)}
          <div class="expanded-cols">
            <div class="body-html">${bodyCache.get(record.id) || ""}</div>
            <aside class="meta-panel">
              <p class="meta-section-label">Details</p>
              ${classificationNote(record)}
              <div class="meta-grid">
                ${facetChips("Commodities", record.commodities)}
                ${facetChips("Systems", record.systems)}
                ${facetChips("Vehicle Categories", record.vehicle_categories)}
                ${facetChips("Open Tags", record.open_tags, "open")}
                ${unChips("UN Equivalent", record.un_equivalent, false)}
                ${unChips("AI-Suggested Equivalent", record.un_equivalent_ai, true)}
                ${relatedLinks(record.related)}
                ${sourceHtml ? `<div class="meta-item"><strong>Source</strong><span>${sourceHtml}</span></div>` : ""}
                ${record.effective_date ? `<div class="meta-item"><strong>Effective Date</strong><span>${escapeHtml(record.effective_date)}</span></div>` : ""}
                ${record.last_amended ? `<div class="meta-item"><strong>Last Amended</strong><span>${escapeHtml(record.last_amended)}</span></div>` : ""}
                ${record.last_pulled ? `<div class="meta-item"><strong>Last Pulled</strong><span>${escapeHtml(record.last_pulled)}</span></div>` : ""}
                ${record.tagged_at  ? `<div class="meta-item"><strong>Tagged At</strong><span>${escapeHtml(record.tagged_at)}</span></div>`  : ""}
              </div>
            </aside>
          </div>
        </div>
      `;
    }

    // Breadcrumb back to the result set the reader was opened from, so the
    // search/filter context isn't lost (matters most on mobile, where the
    // reader fully overlays the results).
    function readerContextLabel() {
      const parts = [];
      const q = searchInput.value.trim();
      if (q) parts.push(`“${q}”`);
      const sel = readSelections();
      FILTERS.forEach((f) => { sel[f.key].forEach((v) => parts.push(displayLabel(v))); });
      return parts.length ? `Back to ${parts.join(" · ")}` : "Back to all regulations";
    }

    async function openReader(id) {
      const record = recordById.get(id);
      if (!record) return;
      openReaderId = id;
      if (!bodyCache.has(id)) {
        try {
          const data = await fetch(`data/records/${encodeURIComponent(id)}.json`).then((r) => r.json());
          bodyCache.set(id, data.body_html || "");
        } catch { bodyCache.set(id, "<p>Failed to load regulation text.</p>"); }
      }
      if (openReaderId !== id) return;  // superseded by a later open/close during the await
      const backLabel = document.querySelector("#reader-back-label");
      if (backLabel) backLabel.textContent = readerContextLabel();
      document.querySelector("#reader-title").textContent = record.title || record.id;
      document.querySelector("#reader-trust").innerHTML = readerTrustHtml(record);
      document.querySelector("#reader-body").innerHTML = readerBodyHtml(record);
      document.querySelector("#reader").classList.remove("hidden");
      document.querySelector(".layout").classList.add("reading");
      document.querySelector("#reader-close").focus();
      render();
      syncUrl();
    }

    function closeReader({ restoreFocus = true } = {}) {
      openReaderId = null;
      document.querySelector("#reader").classList.add("hidden");
      document.querySelector(".layout").classList.remove("reading");
      document.querySelector("#reader-trust").innerHTML = "";
      render();   // rebuilds the cards DOM, so re-query the origin button by id below
      syncUrl();
      if (restoreFocus && readerOrigin) {
        const originBtn = cards.querySelector(`[data-read="${CSS.escape(readerOrigin)}"]`);
        if (originBtn) originBtn.focus();
      }
    }

    function baseSearchText(record) {
      return [
        record.title, record.citation,
        (record.aliases || []).join(" "),
        record.summary_text,
        (record.un_equivalent || []).join(" "),
        (record.tags || []).join(" "),
        (record.open_tags || []).join(" "),
      ].join(" ");
    }

    function bodyMatchSnippet(record, query) {
      const q = normalize(query).trim();
      if (!q || q.length < 3 || normalize(baseSearchText(record)).includes(q)) return "";
      const text = searchDocsById.get(record.id) || "";
      const lower = normalize(text);
      const idx = lower.indexOf(q);
      if (idx < 0) return "";
      const start = Math.max(0, idx - 90);
      const end = Math.min(text.length, idx + q.length + 140);
      const prefix = start > 0 ? "..." : "";
      const suffix = end < text.length ? "..." : "";
      return `${prefix}${text.slice(start, end).trim()}${suffix}`;
    }

    function summaryMetaHtml(record) {
      if (!record.summary_ai) return "";
      const tags = [`<span class="summary-tag">AI summary</span>`];
      if (record.summary_stale) {
        // Static literal — no record data is interpolated, so no escapeHtml needed.
        tags.push(`<span class="summary-tag summary-stale" title="The source text changed after this summary was written.">may be out of date</span>`);
      }
      return `<p class="summary-meta">${tags.join("")}</p>`;
    }

    function cardSummaryHtml(record, query) {
      const snippet = bodyMatchSnippet(record, query);
      if (snippet) return `<p class="summary summary-snippet">${highlight(snippet, query)}</p>`;
      const summary = `<p class="summary">${highlight(record.summary_text || "No summary available.", query)}</p>`;
      return summary + summaryMetaHtml(record);
    }

    // Trust footer on each card: source authority + freshness. Lets a reader
    // gauge how current and how authoritative a result is without opening it.
    function cardFootHtml(record) {
      const bits = [];
      const host = record.source_url ? hostLabel(record.source_url) : "";
      if (host) bits.push(`<span class="card-source">${escapeHtml(host)}</span>`);
      if (record.last_pulled) bits.push(`<span class="card-fresh">Updated ${escapeHtml(record.last_pulled.slice(0, 10))}</span>`);
      if (!bits.length) return "";
      return `<p class="card-foot">${bits.join('<span class="dot" aria-hidden="true">·</span>')}</p>`;
    }

    function cardTemplate(record) {
      const q = searchInput.value;
      const isActive = record.id === openReaderId;
      const statusBadge = record.status && record.status !== "in-force"
        ? `<span class="badge ${statusClass(record.status)}">${escapeHtml(displayLabel(record.status))}</span>` : "";
      return `
        <article class="reg-card${isActive ? " is-reading" : ""}" id="reg-${slug(record.id)}">
          <div class="card-top">
            <div>
              <h2 class="reg-title">${highlight(record.title || record.id, q)}</h2>
              <div class="badges">
                <span class="badge region">${escapeHtml(record.region)}</span>
                <span class="badge">${escapeHtml(record.citation)}</span>
                ${statusBadge}
              </div>
              ${cardSummaryHtml(record, q)}
              ${cardFootHtml(record)}
            </div>
            <button type="button" class="expand-button" data-read="${escapeHtml(record.id)}" aria-expanded="${isActive}">
              ${isActive ? "Reading" : "Read"}
            </button>
          </div>
        </article>`;
    }

    const AVAIL_LABELS = { full: "Full text", paywall: "Paywall", noconn: "No live connection" };

    function renderChips() {
      const bar = document.querySelector("#chip-bar");
      const chips = [];
      const q = searchInput.value.trim();
      if (q) chips.push({ type: "q", label: `Search: "${q}"` });
      const sel = readSelections();
      FILTERS.forEach((f) => {
        Array.from(sel[f.key]).forEach((v) => {
          chips.push({ type: "facet", key: f.key, value: v, label: `${f.label}: ${displayLabel(v)}` });
        });
      });
      const shown = AVAIL_CATEGORIES.filter((c) => selectedAvailability().has(c));
      const isDefault = shown.length === 1 && shown[0] === "full";
      if (!isDefault) {
        if (shown.length === 0) {
          // All availability boxes unchecked: a non-default state that would
          // otherwise show no chip. Surface a removable "nothing" chip so the
          // default (full text) is always restorable from the chip bar.
          chips.push({ type: "avail-none", label: "Show: nothing" });
        } else {
          shown.forEach((c) => chips.push({ type: "avail", value: c, label: `Show: ${AVAIL_LABELS[c]}` }));
        }
      }
      if (chips.length === 0) { bar.classList.add("hidden"); bar.innerHTML = ""; return; }
      bar.classList.remove("hidden");
      bar.innerHTML = chips.map((c) =>
        `<span class="active-chip" data-chip-type="${c.type}"${c.key ? ` data-chip-key="${escapeHtml(c.key)}"` : ""}${c.value !== undefined ? ` data-chip-value="${escapeHtml(c.value)}"` : ""}>`
        + `${escapeHtml(c.label)}<button type="button" class="chip-x" aria-label="Remove">×</button></span>`
      ).join("") + `<button type="button" class="chip-clear-all" id="chip-clear-all">Clear all</button>`;
    }

    function regionGroupLabel(region) {
      const meta = (TAXONOMY.region_series || {})[region];
      if (meta && meta.series) return `${meta.name || region} · ${meta.series}`;
      return (meta && meta.name) || region;
    }

    function areaSelected() {
      const sel = readSelections();
      return sel.systems.size > 0 || sel.commodities.size > 0;
    }

    function renderGrouped(renderable) {
      const groups = new Map();
      renderable.forEach((r) => {
        if (!groups.has(r.region)) groups.set(r.region, []);
        groups.get(r.region).push(r);
      });
      const order = Array.from(groups.keys()).sort((a, b) => groups.get(b).length - groups.get(a).length);
      return order.map((region) => {
        const recs = groups.get(region);
        return `<div class="market-group"><h3 class="market-group-head">${escapeHtml(regionGroupLabel(region))} <span class="market-group-count">(${recs.length})</span></h3>`
          + recs.map(cardTemplate).join("") + `</div>`;
      }).join("");
    }

    function render() {
      const visible    = getVisibleRecords();
      const renderable = visible.slice(0, visibleLimit);
      resultCount.textContent = `Showing ${renderable.length} of ${visible.length}`;
      const orderEl = document.querySelector("#result-order");
      if (orderEl) orderEl.textContent = areaSelected() ? "Grouped by market" : "Sorted by repository order";
      cards.innerHTML = renderable.length
        ? (areaSelected() ? renderGrouped(renderable) : renderable.map(cardTemplate).join(""))
        : '<div class="empty-state">No regulations match the current filters.</div>';
      loadMore.classList.toggle("hidden", visible.length <= visibleLimit);
      updateFacetCounts(visible);
      renderChips();
    }

    function buildFilters() {
      const DEFAULT_OPEN = new Set(["region"]);
      function sectionHtml(filter) {
        const options = (TAXONOMY[filter.taxonomyKey] || [])
          .filter((value) => (CORPUS_COUNTS[filter.key]?.[value] || 0) > 0)
          .sort((a, b) => (CORPUS_COUNTS[filter.key][b] || 0) - (CORPUS_COUNTS[filter.key][a] || 0));
        if (options.length < 2) return "";
        const controls = options.map((value) => {
          const id = `${filter.key}-${slug(value)}`;
          return `
            <label class="facet-option" for="${escapeHtml(id)}">
              <input type="checkbox" id="${escapeHtml(id)}" name="${escapeHtml(filter.key)}" value="${escapeHtml(value)}">
              <span>${escapeHtml(displayLabel(value))}</span>
              <span class="facet-count" data-facet="${escapeHtml(filter.key)}" data-value="${escapeHtml(value)}" aria-hidden="true">0</span>
            </label>`;
        }).join("");
        const infoIcon = filter.tooltip
          ? `<button type="button" class="filter-info" data-tooltip="${escapeHtml(filter.tooltip)}" aria-label="${escapeHtml(filter.label)} help">i</button>`
          : "";
        return `
          <details${DEFAULT_OPEN.has(filter.key) ? " open" : ""}>
            <summary>${escapeHtml(filter.label)}${infoIcon}</summary>
            <div class="facet-options collapsed" data-facet="${escapeHtml(filter.key)}">${controls}</div>
            <button type="button" class="facet-more" data-more="${escapeHtml(filter.key)}"></button>
          </details>`;
      }
      const primary = FILTERS.filter((f) => PRIMARY_FILTERS.has(f.key)).map(sectionHtml).join("");
      const secondary = FILTERS.filter((f) => !PRIMARY_FILTERS.has(f.key)).map(sectionHtml).join("");
      filtersForm.innerHTML = primary
        + (secondary.trim()
            ? `<details class="more-filters"><summary>More filters</summary><div>${secondary}</div></details>`
            : "");
    }

    // Per-facet "show all" state — facets start collapsed, hiding options with
    // no matches in the current view (e.g. all-stub regions under "Full text").
    const facetShowAll = new Set();
    function updateFacetCollapse() {
      filtersForm.querySelectorAll(".facet-options[data-facet]").forEach((box) => {
        const key = box.dataset.facet;
        const hiddenCount = box.querySelectorAll(".facet-option.empty").length;
        const expanded = facetShowAll.has(key);
        box.classList.toggle("collapsed", !expanded);
        const btn = filtersForm.querySelector(`.facet-more[data-more="${key}"]`);
        if (!btn) return;
        if (hiddenCount === 0 && !expanded) {
          btn.classList.remove("visible");
        } else {
          btn.classList.add("visible");
          const label = FACET_MORE_LABELS[key] || "options";
          btn.textContent = expanded ? "Show fewer" : `Show ${hiddenCount} more ${label}`;
        }
      });
    }

    function valuesFromParams(params, key) {
      return params.getAll(key).flatMap((v) => v.split(",")).filter(Boolean);
    }

    function workspaceActive() {
      // Explicit view markers win (used by Home-link and the browse-all link).
      const view = new URLSearchParams(window.location.search).get("view");
      if (view === "home") return false;
      if (view === "results") return true;
      if (new URLSearchParams(window.location.search).get("id")) return true;
      // Otherwise decide from LIVE state — the URL lags behind because syncUrl()
      // is debounced, so reading it here would miss the just-typed query/facet.
      if (searchInput.value.trim()) return true;
      if (filtersForm.querySelector("input:checked")) return true;
      const shown = AVAIL_CATEGORIES.filter((c) => selectedAvailability().has(c));
      return !(shown.length === 1 && shown[0] === "full");
    }

    function route() {
      const onWorkspace = workspaceActive();
      // Leaving the Workspace (e.g. Home link) must also dismiss any open reader,
      // otherwise its DOM/.reading state resurfaces when the Workspace returns.
      if (!onWorkspace && openReaderId) {
        closeReader({ restoreFocus: false });
      }
      homeView.classList.toggle("hidden", onWorkspace);
      workspaceEls.forEach((el) => el && el.classList.toggle("hidden", !onWorkspace));
      if (!onWorkspace) renderHome();
    }

    function topByCount(key, n) {
      const counts = CORPUS_COUNTS[key] || {};
      return Object.keys(counts)
        .filter((v) => counts[v] > 0)
        .sort((a, b) => counts[b] - counts[a])
        .slice(0, n);
    }

    // Freshness signal: the most recent pull across the corpus. ISO-8601 strings
    // compare lexicographically, so a string max is a valid date max.
    function latestPullDate() {
      let max = "";
      REGS.forEach((r) => { if (r.last_pulled && r.last_pulled > max) max = r.last_pulled; });
      return max ? max.slice(0, 10) : "";
    }

    function renderHeroFeature() {
      const counts = CORPUS_COUNTS.systems || {};
      const top = topByCount("systems", 6);
      const chipsEl = document.querySelector("#hero-chips");
      if (chipsEl) {
        chipsEl.innerHTML = top.map((v) =>
          `<button type="button" class="hero-chip" data-dir-key="systems" data-dir-value="${escapeHtml(v)}">`
          + `${escapeHtml(displayLabel(v))}<span class="hero-chip-count">${counts[v]}</span></button>`
        ).join("");
      }
      const listEl = document.querySelector("#feature-list");
      if (listEl) {
        listEl.innerHTML = top.map((v) =>
          `<li><button type="button" class="feature-item" data-dir-key="systems" data-dir-value="${escapeHtml(v)}" aria-label="${escapeHtml(displayLabel(v))} — ${counts[v]} regulations">`
          + `<span class="feature-rank" aria-hidden="true"></span>`
          + `<span class="feature-name">${escapeHtml(displayLabel(v))}</span>`
          + `<span class="feature-count">${counts[v]}</span></button></li>`
        ).join("");
      }
      const foot = document.querySelector("#feature-foot");
      if (foot) {
        const fresh = latestPullDate();
        // Honest label: ranked by how many regulations we hold per system
        // (real coverage), not by usage — this is a static site with no analytics.
        foot.innerHTML = fresh
          ? `<span class="fresh-dot">&#9679;</span> Ranked by coverage · repository updated ${escapeHtml(fresh)}`
          : `Ranked by coverage`;
      }
    }

    const EXAMPLE_QUERIES = ["FMVSS 208", "braking", "airbag", "UN R13", "lighting"];
    function renderExamples() {
      const el = document.querySelector("#search-examples");
      if (!el) return;
      el.innerHTML = `Try `
        + EXAMPLE_QUERIES.map((q) =>
            `<button type="button" class="example-q" data-example="${escapeHtml(q)}">${escapeHtml(q)}</button>`
          ).join(", ");
    }

    function maybeShowOnboard() {
      const el = document.querySelector("#onboard");
      if (!el) return;
      el.classList.toggle("hidden", localStorage.getItem("onboarded") === "1");
    }

    function renderHome() {
      const total = REGS.length;
      const tagged = (CORPUS_COUNTS.tagging_status && CORPUS_COUNTS.tagging_status["llm-tagged"]) || 0;
      const untagged = (CORPUS_COUNTS.tagging_status && CORPUS_COUNTS.tagging_status["untagged"]) || 0;
      const markets = Object.keys(CORPUS_COUNTS.region || {}).length;
      const cov = document.querySelector("#coverage-line");
      cov.innerHTML = `<strong>${total}</strong> regulations · ${tagged} classified by part &amp; system · ${markets} markets`
        + (untagged ? ` · ${untagged} untagged` : "")
        + ` <a class="browse-all" href="?view=results" data-browse-all>Browse all by market →</a>`;

      renderHeroFeature();
      renderExamples();
      if (homeSearch) homeSearch.value = searchInput.value;
      maybeShowOnboard();

      renderDirPanel("systems", (v) => displayLabel(v));
      renderDirPanel("commodities", (v) => displayLabel(v));
      renderDirPanel("region", (v) => marketTileLabel(v));
    }

    function renderDirPanel(key, labelFn) {
      const counts = CORPUS_COUNTS[key] || {};
      let values = Object.keys(counts).filter((v) => counts[v] > 0);
      if (homeSort[key] === "az") {
        values.sort((a, b) => labelFn(a).localeCompare(labelFn(b)));
      } else {
        values.sort((a, b) => counts[b] - counts[a]);
      }
      const showAll = homeShowAll[key];
      const shown = showAll ? values : values.slice(0, HOME_TOP_N);
      const tiles = shown.map((v) =>
        `<button type="button" class="dir-tile" data-dir-key="${escapeHtml(key)}" data-dir-value="${escapeHtml(v)}">`
        + `<span>${escapeHtml(labelFn(v))}</span><span class="dir-count">${counts[v]}</span></button>`
      ).join("");
      document.querySelector(`[data-tiles="${key}"]`).innerHTML = tiles;

      const sortEl = document.querySelector(`[data-sort-for="${key}"]`);
      const az = homeSort[key] === "az";
      sortEl.innerHTML = `Sort: `
        + `<button data-set-sort="${key}" data-sort="az" class="${az ? "active" : ""}">A–Z</button> | `
        + `<button data-set-sort="${key}" data-sort="count" class="${az ? "" : "active"}">Count</button>`;

      const moreBtn = document.querySelector(`[data-more-for="${key}"]`);
      const hidden = values.length - shown.length;
      if (hidden > 0 || showAll) {
        moreBtn.classList.remove("hidden");
        moreBtn.textContent = showAll ? "Show fewer" : `Show all (${hidden} more)`;
      } else {
        moreBtn.classList.add("hidden");
      }
    }

    function goToWorkspace(paramKey, paramValue) {
      const params = new URLSearchParams();
      if (paramKey) params.append(paramKey, paramValue);
      const qs = params.toString();
      history.replaceState(null, "", qs ? `${window.location.pathname}?${qs}` : window.location.pathname);
      applyUrlParams();   // sets the facet checkboxes / search box from the URL
      visibleLimit = PAGE_SIZE;
      route();            // workspaceActive() returns true -> shows Workspace
      render();
      updateClearButton();
      window.scrollTo(0, 0);
    }

    function applyUrlParams() {
      const params = new URLSearchParams(window.location.search);
      searchInput.value = params.get("q") || "";
      // Content-availability bar. Default (no param) = full text only.
      // "avail=full,paywall" lists shown categories; "avail=none" = nothing shown.
      const availParam = params.get("avail");
      const shown = availParam === null
        ? new Set(["full"])
        : new Set(availParam.split(",").filter(Boolean));
      availBoxes.forEach((b) => { b.checked = shown.has(b.dataset.avail); });
      FILTERS.forEach((f) => {
        const selected = new Set(valuesFromParams(params, f.key));
        filtersForm.querySelectorAll(`input[name="${f.key}"]`).forEach((el) => {
          el.checked = selected.has(el.value);
        });
      });
      const idParam = params.get("id");
      if (idParam && recordById.get(idParam)) { openReader(idParam); }
      else if (!idParam && openReaderId) { closeReader(); }
    }

    function syncUrl() {
      window.clearTimeout(urlTimer);
      urlTimer = window.setTimeout(() => {
        const params = new URLSearchParams();
        const q = searchInput.value.trim();
        if (q) params.set("q", q);
        // Only record availability in the URL when it differs from the default
        // (full text only). "none" round-trips the all-unchecked state.
        const shown = AVAIL_CATEGORIES.filter((c) => selectedAvailability().has(c));
        const isDefault = shown.length === 1 && shown[0] === "full";
        if (!isDefault) params.set("avail", shown.length ? shown.join(",") : "none");
        const sel = readSelections();
        FILTERS.forEach((f) => {
          Array.from(sel[f.key]).forEach((v) => params.append(f.key, v));
        });
        if (openReaderId) params.set("id", openReaderId);
        const qs = params.toString();
        history.replaceState(null, "", qs ? `${window.location.pathname}?${qs}` : window.location.pathname);
      }, 150);
    }

    searchInput.addEventListener("input", () => {
      visibleLimit = PAGE_SIZE;
      render();
      syncUrl();
      updateClearButton();
      route();
    });

    // The hero search is a promoted proxy for the header search: forward its
    // value, then the normal pipeline routes Home -> Workspace on first keystroke.
    // That first keystroke hides #home (and with it #home-search), so hand focus
    // to the header search — which already mirrors the value — so typing continues
    // seamlessly instead of dropping to <body>.
    if (homeSearch) {
      homeSearch.addEventListener("input", () => {
        searchInput.value = homeSearch.value;
        visibleLimit = PAGE_SIZE;
        render();
        syncUrl();
        updateClearButton();
        route();
        if (homeView.classList.contains("hidden")) {
          searchInput.focus();
          try {
            const end = searchInput.value.length;
            searchInput.setSelectionRange(end, end);
          } catch { /* setSelectionRange unsupported on some inputs */ }
        }
      });
    }

    filtersForm.addEventListener("change", () => {
      visibleLimit = PAGE_SIZE;
      render();
      syncUrl();
      updateClearButton();
      route();
    });

    // "Show all / Show fewer" toggles per-facet reveal of zero-match options.
    filtersForm.addEventListener("click", (event) => {
      const more = event.target.closest(".facet-more");
      if (!more) return;
      const key = more.dataset.more;
      facetShowAll.has(key) ? facetShowAll.delete(key) : facetShowAll.add(key);
      updateFacetCollapse();
    });

    const filtersRail   = document.querySelector(".filters");
    const filtersToggle = document.querySelector("#filters-toggle");
    const filtersClose  = document.querySelector("#filters-close");

    function setFiltersOpen(open) {
      filtersRail.classList.toggle("is-open", open);
      filtersToggle.setAttribute("aria-expanded", String(open));
    }

    filtersToggle.addEventListener("click", () => {
      setFiltersOpen(!filtersRail.classList.contains("is-open"));
    });
    filtersClose.addEventListener("click", () => {
      setFiltersOpen(false);
      filtersToggle.focus();
    });

    availBoxes.forEach((box) => box.addEventListener("change", () => {
      visibleLimit = PAGE_SIZE;
      render();
      syncUrl();
      route();
    }));

    cards.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-read]");
      if (!btn) return;
      const id = btn.getAttribute("data-read");
      if (id === openReaderId) { closeReader(); } else { readerOrigin = id; openReader(id); }
    });

    // Cross-reference links (UN equivalents, AI-suggested, related) inside the
    // reader open the target record in place. The real ?id= href preserves
    // ctrl/middle-click (new tab) and no-JS fallback; left-click stays in-app.
    document.querySelector("#reader-body").addEventListener("click", (event) => {
      const link = event.target.closest("a[data-read]");
      if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
      event.preventDefault();
      const id = link.getAttribute("data-read");
      if (id && id !== openReaderId) openReader(id);
    });

    document.querySelector("#reader-close").addEventListener("click", () => closeReader());
    document.querySelector("#reader-back").addEventListener("click", () => closeReader());

    loadMore.addEventListener("click", () => {
      visibleLimit += PAGE_SIZE;
      render();
    });

    clearFilters.addEventListener("click", () => {
      searchInput.value = "";
      filtersForm.querySelectorAll("input[type='checkbox']").forEach((el) => { el.checked = false; });
      availBoxes.forEach((b) => { b.checked = b.dataset.avail === "full"; });
      visibleLimit = PAGE_SIZE;
      render();
      syncUrl();
      updateClearButton();
      route();   // all cleared -> Home, which also dismisses any open reader
      searchInput.focus();
    });

    document.querySelector("#chip-bar").addEventListener("click", (event) => {
      if (event.target.closest("#chip-clear-all")) { clearFilters.click(); return; }
      const x = event.target.closest(".chip-x");
      if (!x) return;
      const chip = x.closest(".active-chip");
      const type = chip.dataset.chipType;
      if (type === "q") { searchInput.value = ""; }
      else if (type === "facet") {
        const el = filtersForm.querySelector(`input[name="${chip.dataset.chipKey}"][value="${CSS.escape(chip.dataset.chipValue)}"]`);
        if (el) el.checked = false;
      } else if (type === "avail") {
        const el = availBoxes.find((b) => b.dataset.avail === chip.dataset.chipValue);
        if (el) el.checked = false;
      } else if (type === "avail-none") {
        // Restore the default availability (full text only).
        availBoxes.forEach((b) => { b.checked = b.dataset.avail === "full"; });
      }
      visibleLimit = PAGE_SIZE;
      render();
      syncUrl();
      updateClearButton();
      route();
    });

    copyLink.addEventListener("click", () => {
      const url = window.location.href;
      const prev = copyLink.textContent;
      navigator.clipboard.writeText(url).then(() => {
        copyLink.textContent = "Copied!";
        setTimeout(() => { copyLink.textContent = prev; }, 1500);
      }).catch(() => {
        const inp = Object.assign(document.createElement("input"), { value: url });
        document.body.appendChild(inp);
        inp.select();
        document.execCommand("copy");
        document.body.removeChild(inp);
        copyLink.textContent = "Copied!";
        setTimeout(() => { copyLink.textContent = prev; }, 1500);
      });
    });

    homeLink.addEventListener("click", () => {
      history.replaceState(null, "", window.location.pathname);
      searchInput.value = "";
      filtersForm.querySelectorAll("input[type='checkbox']").forEach((el) => { el.checked = false; });
      availBoxes.forEach((b) => { b.checked = b.dataset.avail === "full"; });
      visibleLimit = PAGE_SIZE;
      render();
      updateClearButton();
      route();
    });

    homeView.addEventListener("click", (event) => {
      if (event.target.closest("#onboard-dismiss")) {
        localStorage.setItem("onboarded", "1");
        document.querySelector("#onboard").classList.add("hidden");
        return;
      }
      const example = event.target.closest(".example-q");
      if (example) {
        searchInput.value = example.dataset.example;
        if (homeSearch) homeSearch.value = example.dataset.example;
        visibleLimit = PAGE_SIZE;
        render();
        syncUrl();
        updateClearButton();
        route();
        window.scrollTo(0, 0);
        return;
      }
      // dir tiles, hero quick-chips, and the featured leaderboard all carry
      // data-dir-key / data-dir-value and jump straight into the workspace.
      const jump = event.target.closest("[data-dir-value]");
      if (jump) {
        goToWorkspace(jump.dataset.dirKey, jump.dataset.dirValue);
        return;
      }
      const browseAll = event.target.closest("[data-browse-all]");
      if (browseAll) {
        event.preventDefault();
        // Mark the workspace in the URL FIRST, then route, so workspaceActive() returns true.
        history.replaceState(null, "", `${window.location.pathname}?view=results`);
        applyUrlParams();
        visibleLimit = PAGE_SIZE;
        route();
        render();
        updateClearButton();
        window.scrollTo(0, 0);
        return;
      }
      const sortBtn = event.target.closest("[data-set-sort]");
      if (sortBtn) {
        homeSort[sortBtn.dataset.setSort] = sortBtn.dataset.sort;
        renderHome();
        return;
      }
      const moreBtn = event.target.closest("[data-more-for]");
      if (moreBtn) {
        const k = moreBtn.dataset.moreFor;
        homeShowAll[k] = !homeShowAll[k];
        renderHome();
        return;
      }
    });

    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const isTyping = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target.isContentEditable;
      if ((event.key === "k" || event.key === "K") && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        searchInput.focus();
        searchInput.select();
        return;
      }
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        searchInput.focus();
      }
      if (event.key === "Escape") {
        if (openReaderId) { event.preventDefault(); closeReader(); return; }
        if (filtersRail.classList.contains("is-open")) {
          event.preventDefault(); setFiltersOpen(false); filtersToggle.focus(); return;
        }
      }
    });

    async function boot() {
      const [regs, taxonomy] = await Promise.all([
        fetch("data/index.json").then((r) => r.json()),
        fetch("data/taxonomy.json").then((r) => r.json()),
      ]);
      REGS = regs;
      TAXONOMY = taxonomy;
      recordById = new Map(REGS.map((r) => [r.id, r]));
      UN_INDEX = (TAXONOMY && TAXONOMY.un_index) || {};
      rebuildCorpusCounts();
      buildFilters();
      applyUrlParams();
      render();
      updateClearButton();
      route();
      if (typeof requestIdleCallback === "function") { requestIdleCallback(loadSearch); }
      else { setTimeout(loadSearch, 0); }
    }
    boot().catch((err) => {
      cards.innerHTML = '<div class="empty-state">Failed to load regulation data. Check the console for details.</div>';
      console.error("boot failed:", err);
    });

    (function () {
      const tip = document.getElementById("tip");
      function showTip(el) {
        tip.textContent = el.dataset.tooltip;
        tip.style.display = "block";
        tip.setAttribute("aria-hidden", "false");
        const r = el.getBoundingClientRect();
        const tw = tip.offsetWidth;
        const left = (r.right + 10 + tw > window.innerWidth) ? r.left - tw - 10 : r.right + 10;
        tip.style.left = left + "px";
        tip.style.top  = Math.max(8, r.top - 2) + "px";
      }
      function hideTip() { tip.style.display = "none"; tip.setAttribute("aria-hidden", "true"); }
      document.addEventListener("mouseover", (e) => { const el = e.target.closest("[data-tooltip]"); if (el) showTip(el); else hideTip(); });
      document.addEventListener("mouseout",  (e) => { if (!e.relatedTarget || !e.relatedTarget.closest("[data-tooltip]")) hideTip(); });
      document.addEventListener("focusin",   (e) => { const el = e.target.closest("[data-tooltip]"); if (el) showTip(el); });
      document.addEventListener("focusout",  (e) => { if (!e.relatedTarget || !e.relatedTarget.closest("[data-tooltip]")) hideTip(); });
    })();

    (function () {
      const root = document.documentElement;
      const btn = document.getElementById("theme-toggle");
      function systemTheme() {
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      }
      function applyTheme(t) {
        root.setAttribute("data-theme", t);
        btn.textContent = t === "dark" ? "Light" : "Dark";
      }
      applyTheme(localStorage.getItem("theme") || "light");
      btn.addEventListener("click", function () {
        const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        localStorage.setItem("theme", next);
        applyTheme(next);
      });
    })();