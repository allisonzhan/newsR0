/**
 * newsR0 — Frontend application
 * Vanilla JS, no build step required.
 */

const API_BASE = "/api";
const PAGE_SIZE = 50;

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  q: "",
  sectors: [],          // selected top-level sectors
  subSectors: [],       // selected sub-sectors
  sources: [],          // selected sources (empty = all)
  dateRange: "7d",      // 24h | 7d | 30d | all
  offset: 0,
  total: 0,
  articles: [],
  allSectors: [],       // taxonomy from /api/sectors
  allSources: [],       // source list from /api/sources
  refreshing: false,
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const searchInput       = $("search-input");
const refreshBtn        = $("refresh-btn");
const refreshSpinner    = $("refresh-spinner");
const lastRefreshLabel  = $("last-refresh-label");
const activeFiltersBar  = $("active-filters");
const filterChips       = $("filter-chips");
const clearAllBtn       = $("clear-all-btn");
const sectorList        = $("sector-list");
const sourceList        = $("source-list");
const articleList       = $("article-list");
const feedStatus        = $("feed-status");
const loadMoreBtn       = $("load-more-btn");
const loadMoreContainer = $("load-more-container");

// ── Helpers ────────────────────────────────────────────────────────────────
function relativeTime(isoString) {
  if (!isoString) return "";
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 2)  return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function dateRangeToISO(range) {
  const now = new Date();
  if (range === "24h") {
    const d = new Date(now); d.setHours(d.getHours() - 24);
    return d.toISOString();
  }
  if (range === "7d") {
    const d = new Date(now); d.setDate(d.getDate() - 7);
    return d.toISOString();
  }
  if (range === "30d") {
    const d = new Date(now); d.setDate(d.getDate() - 30);
    return d.toISOString();
  }
  return null; // "all"
}

function buildQuery(offset = 0) {
  const params = new URLSearchParams();
  if (state.q)            params.set("q", state.q);
  if (state.sectors.length)   params.set("sector", state.sectors.join(","));
  if (state.subSectors.length) params.set("sub_sector", state.subSectors.join(","));
  if (state.sources.length)   params.set("source", state.sources.join(","));
  const fromDate = dateRangeToISO(state.dateRange);
  if (fromDate) params.set("from_date", fromDate);
  params.set("limit", PAGE_SIZE);
  params.set("offset", offset);
  return params.toString();
}

// ── API calls ──────────────────────────────────────────────────────────────
async function fetchArticles(append = false) {
  if (!append) {
    state.offset = 0;
    state.articles = [];
  }
  setRefreshing(true);
  feedStatus.textContent = "Loading…";

  try {
    const res = await fetch(`${API_BASE}/articles?${buildQuery(state.offset)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.total = data.total;
    state.articles = append ? [...state.articles, ...data.articles] : data.articles;
    state.offset += data.articles.length;
    renderArticles(append);
    feedStatus.textContent = `${state.total.toLocaleString()} article${state.total !== 1 ? "s" : ""} found`;
    lastRefreshLabel.textContent = `Last refresh: ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    feedStatus.textContent = `Error loading articles: ${err.message}`;
    console.error(err);
  } finally {
    setRefreshing(false);
  }
}

async function fetchSectors() {
  try {
    const res = await fetch(`${API_BASE}/sectors`);
    state.allSectors = await res.json();
    renderSectorSidebar();
  } catch (err) {
    console.error("Failed to load sectors:", err);
  }
}

async function fetchSources() {
  try {
    const res = await fetch(`${API_BASE}/sources`);
    state.allSources = await res.json();
    renderSourceSidebar();
  } catch (err) {
    console.error("Failed to load sources:", err);
  }
}

async function triggerRefresh() {
  setRefreshing(true);
  refreshBtn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/refresh`, { method: "POST" });
    const data = await res.json();
    // Poll until the run completes (simple approach)
    await pollRunStatus(data.run_id);
    await fetchArticles();
    await fetchSources();
  } catch (err) {
    console.error("Refresh failed:", err);
  } finally {
    setRefreshing(false);
    refreshBtn.disabled = false;
  }
}

async function pollRunStatus(runId) {
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 3000));
    try {
      const res = await fetch(`${API_BASE}/runs/${runId}`);
      const run = await res.json();
      if (run.status === "success" || run.status === "failed") return;
    } catch (_) {}
  }
}

// ── Render ─────────────────────────────────────────────────────────────────
function renderArticles(append = false) {
  if (!append) articleList.innerHTML = "";

  if (state.articles.length === 0) {
    articleList.innerHTML = `
      <div class="empty-state">
        <h2>No articles found</h2>
        <p>Try broadening your search or adjusting the filters.</p>
      </div>`;
    loadMoreContainer.classList.add("hidden");
    return;
  }

  state.articles.forEach((art, i) => {
    if (append && i < state.offset - PAGE_SIZE) return;
    const card = document.createElement("article");
    card.className = "article-card";
    card.innerHTML = `
      <div class="article-meta">
        <span class="article-source">${escHtml(art.source)}</span>
        <span class="article-time">${relativeTime(art.published_at)}</span>
        ${art.sector ? `<span class="sector-badge">${escHtml(art.sector)}</span>` : ""}
      </div>
      <a class="article-title" href="${escHtml(art.url)}" target="_blank" rel="noopener noreferrer">
        ${escHtml(art.title)}
      </a>
      ${art.excerpt ? `<p class="article-excerpt">${escHtml(art.excerpt)}</p>` : ""}
    `;
    articleList.appendChild(card);
  });

  // Show / hide Load More
  if (state.offset < state.total) {
    loadMoreContainer.classList.remove("hidden");
  } else {
    loadMoreContainer.classList.add("hidden");
  }
}

function renderSectorSidebar() {
  sectorList.innerHTML = "";
  state.allSectors.forEach((sector) => {
    const hasChildren = sector.sub_sectors && sector.sub_sectors.length > 0;
    const item = document.createElement("div");
    item.className = "sector-item";

    const label = document.createElement("div");
    label.className = "sector-label";
    label.dataset.sector = sector.name;
    label.innerHTML = `
      <span>${escHtml(sector.name)}</span>
      ${hasChildren ? `<span class="sector-toggle">▸</span>` : ""}
    `;
    label.addEventListener("click", () => toggleSector(sector.name, label, subList));
    item.appendChild(label);

    const subList = document.createElement("div");
    subList.className = "subsector-list";
    if (hasChildren) {
      renderSubSectors(sector.sub_sectors, subList, sector.name);
    }
    item.appendChild(subList);
    sectorList.appendChild(item);
  });
}

function renderSubSectors(subSectors, container, parentPath) {
  subSectors.forEach((sub) => {
    const hasChildren = sub.sub_sectors && sub.sub_sectors.length > 0;
    const fullPath = `${parentPath}.${sub.name}`;

    const label = document.createElement("div");
    label.className = "subsector-label";
    label.dataset.subsector = sub.name;
    label.textContent = sub.name;
    label.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleSubSector(sub.name, label);
    });
    container.appendChild(label);

    if (hasChildren) {
      const nestedList = document.createElement("div");
      nestedList.className = "subsector-list";
      nestedList.style.paddingLeft = "0.75rem";
      renderSubSectors(sub.sub_sectors, nestedList, fullPath);
      container.appendChild(nestedList);
    }
  });
}

function renderSourceSidebar() {
  sourceList.innerHTML = "";
  state.allSources.filter((s) => s.enabled).forEach((src) => {
    const item = document.createElement("div");
    item.className = "source-item";
    item.dataset.source = src.name;

    const dot = document.createElement("span");
    dot.className = "source-status-dot";
    if (src.last_run_status === "success") dot.classList.add("ok");
    else if (src.last_run_status === "failed") dot.classList.add("fail");

    item.appendChild(dot);
    item.appendChild(document.createTextNode(src.name));
    item.addEventListener("click", () => toggleSource(src.name, item));
    sourceList.appendChild(item);
  });
}

function renderChips() {
  filterChips.innerHTML = "";
  const chips = [];

  if (state.q) chips.push({ label: `"${state.q}"`, remove: () => { state.q = ""; searchInput.value = ""; } });
  state.sectors.forEach((s)    => chips.push({ label: `Sector: ${s}`,     remove: () => removeSector(s) }));
  state.subSectors.forEach((s) => chips.push({ label: `Sub: ${s}`,        remove: () => removeSubSector(s) }));
  state.sources.forEach((s)    => chips.push({ label: `Source: ${s}`,     remove: () => removeSource(s) }));
  if (state.dateRange !== "7d") chips.push({ label: `Date: ${state.dateRange}`, remove: () => { state.dateRange = "7d"; document.querySelector('input[name="date-range"][value="7d"]').checked = true; } });

  chips.forEach(({ label, remove }) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.innerHTML = `${escHtml(label)} <span class="chip-remove" title="Remove">×</span>`;
    chip.querySelector(".chip-remove").addEventListener("click", () => { remove(); applyFilters(); });
    filterChips.appendChild(chip);
  });

  if (chips.length > 0) {
    activeFiltersBar.classList.remove("hidden");
  } else {
    activeFiltersBar.classList.add("hidden");
  }
}

// ── Filter toggles ─────────────────────────────────────────────────────────
function toggleSector(name, labelEl, subList) {
  const idx = state.sectors.indexOf(name);
  if (idx === -1) {
    state.sectors.push(name);
    labelEl.classList.add("active");
  } else {
    state.sectors.splice(idx, 1);
    labelEl.classList.remove("active");
  }
  if (subList && subList.children.length > 0) {
    subList.classList.toggle("open");
    const toggle = labelEl.querySelector(".sector-toggle");
    if (toggle) toggle.textContent = subList.classList.contains("open") ? "▾" : "▸";
  }
  applyFilters();
}

function toggleSubSector(name, labelEl) {
  const idx = state.subSectors.indexOf(name);
  if (idx === -1) {
    state.subSectors.push(name);
    labelEl.classList.add("active");
  } else {
    state.subSectors.splice(idx, 1);
    labelEl.classList.remove("active");
  }
  applyFilters();
}

function toggleSource(name, itemEl) {
  const idx = state.sources.indexOf(name);
  if (idx === -1) {
    state.sources.push(name);
    itemEl.classList.add("active");
  } else {
    state.sources.splice(idx, 1);
    itemEl.classList.remove("active");
  }
  applyFilters();
}

function removeSector(name) {
  state.sectors = state.sectors.filter((s) => s !== name);
  document.querySelectorAll(".sector-label").forEach((el) => {
    if (el.dataset.sector === name) el.classList.remove("active");
  });
  applyFilters();
}

function removeSubSector(name) {
  state.subSectors = state.subSectors.filter((s) => s !== name);
  document.querySelectorAll(".subsector-label").forEach((el) => {
    if (el.dataset.subsector === name) el.classList.remove("active");
  });
  applyFilters();
}

function removeSource(name) {
  state.sources = state.sources.filter((s) => s !== name);
  document.querySelectorAll(".source-item").forEach((el) => {
    if (el.dataset.source === name) el.classList.remove("active");
  });
  applyFilters();
}

function clearAllFilters() {
  state.q = "";
  state.sectors = [];
  state.subSectors = [];
  state.sources = [];
  state.dateRange = "7d";
  searchInput.value = "";
  document.querySelectorAll(".sector-label.active").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".subsector-label.active").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".source-item.active").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".subsector-list.open").forEach((el) => el.classList.remove("open"));
  document.querySelector('input[name="date-range"][value="7d"]').checked = true;
  applyFilters();
}

function applyFilters() {
  renderChips();
  fetchArticles();
}

// ── Spinner/state helpers ──────────────────────────────────────────────────
function setRefreshing(on) {
  state.refreshing = on;
  refreshSpinner.classList.toggle("hidden", !on);
}

// ── Security: escape HTML ──────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Event listeners ────────────────────────────────────────────────────────
let searchDebounce;
searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    state.q = searchInput.value.trim();
    applyFilters();
  }, 350);
});

refreshBtn.addEventListener("click", triggerRefresh);
clearAllBtn.addEventListener("click", clearAllFilters);
loadMoreBtn.addEventListener("click", () => fetchArticles(true));

document.querySelectorAll('input[name="date-range"]').forEach((radio) => {
  radio.addEventListener("change", (e) => {
    state.dateRange = e.target.value;
    applyFilters();
  });
});

// ── Bootstrap ──────────────────────────────────────────────────────────────
(async function init() {
  await Promise.all([fetchSectors(), fetchSources()]);
  await fetchArticles();
})();
