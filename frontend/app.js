/**
 * newsR0 — Frontend application
 * Vanilla JS, no build step required.
 */

const API_BASE = "/api";
const PAGE_SIZE = 50;

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  q: "",
  sector: null,         // single selected sector (page-like navigation)
  subSector: null,      // single selected subsector within a sector
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
const sectorList        = $("sector-list");
const sourceList        = $("source-list");
const articleList       = $("article-list");
const feedStatus        = $("feed-status");
const loadMoreBtn       = $("load-more-btn");
const loadMoreContainer = $("load-more-container");

// Debug: verify DOM elements exist
console.log("newsR0: DOM ready check", {
  searchInput: !!searchInput,
  refreshBtn: !!refreshBtn,
  articleList: !!articleList,
  sectorList: !!sectorList,
  sourceList: !!sourceList
});

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
  if (state.sector)       params.set("sector", state.sector);
  if (state.subSector)    params.set("sub_sector", state.subSector);
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
  
  // Add "All Sectors" button
  const allBtn = document.createElement("div");
  allBtn.className = "sector-label" + (state.sector === null ? " active" : "");
  allBtn.textContent = "All Sectors";
  allBtn.dataset.sector = "all";
  allBtn.addEventListener("click", () => selectSector(null, allBtn));
  sectorList.appendChild(allBtn);
  
  state.allSectors.forEach((sector) => {
    const hasChildren = sector.sub_sectors && sector.sub_sectors.length > 0;
    
    // Sector button
    const label = document.createElement("div");
    label.className = "sector-label" + (state.sector === sector.name ? " active" : "");
    label.textContent = sector.name;
    label.dataset.sector = sector.name;
    label.addEventListener("click", () => selectSector(sector.name, label));
    sectorList.appendChild(label);
    
    // Subsectors (shown only if this sector is selected)
    if (hasChildren && state.sector === sector.name) {
      const subContainer = document.createElement("div");
      subContainer.className = "subsector-container";
      
      sector.sub_sectors.forEach((sub) => {
        const subLabel = document.createElement("div");
        subLabel.className = "subsector-label" + (state.subSector === sub.name ? " active" : "");
        subLabel.textContent = sub.name;
        subLabel.dataset.subsector = sub.name;
        subLabel.addEventListener("click", () => selectSubSector(sub.name, subLabel));
        subContainer.appendChild(subLabel);
      });
      
      sectorList.appendChild(subContainer);
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



// ── Filter toggles ─────────────────────────────────────────────────────────
function selectSector(name, labelEl) {
  // Clear previous active sectors
  document.querySelectorAll(".sector-label.active").forEach((el) => el.classList.remove("active"));
  
  state.sector = name;
  state.subSector = null; // Clear subsector when changing sectors
  labelEl.classList.add("active");
  renderSectorSidebar(); // Re-render to show/hide subsectors
  applyFilters();
}

function selectSubSector(name, labelEl) {
  // Clear previous active subsectors
  document.querySelectorAll(".subsector-label.active").forEach((el) => el.classList.remove("active"));
  
  state.subSector = name;
  labelEl.classList.add("active");
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

function removeSource(name) {
  state.sources = state.sources.filter((s) => s !== name);
  document.querySelectorAll(".source-item").forEach((el) => {
    if (el.dataset.source === name) el.classList.remove("active");
  });
  applyFilters();
}

function applyFilters() {
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
loadMoreBtn.addEventListener("click", () => fetchArticles(true));

document.querySelectorAll('input[name="date-range"]').forEach((radio) => {
  radio.addEventListener("change", (e) => {
    state.dateRange = e.target.value;
    applyFilters();
  });
});

// ── Bootstrap ──────────────────────────────────────────────────────────────
(async function init() {
  try {
    console.log("newsR0: Initializing...");
    const [sectorsResult, sourcesResult] = await Promise.all([fetchSectors(), fetchSources()]);
    console.log("newsR0: Sectors and sources loaded:", { sectors: state.allSectors.length, sources: state.allSources.length });
    await fetchArticles();
    console.log("newsR0: Articles loaded:", state.articles.length);
  } catch (err) {
    console.error("newsR0: Initialization failed:", err);
  }
})();
