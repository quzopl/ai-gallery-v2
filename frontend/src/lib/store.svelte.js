import { api, post, del } from "./api.js";

const prefs = (() => { try { return JSON.parse(localStorage.getItem("aig2") || "{}"); } catch { return {}; } })();

export const S = $state({
  libraries: [],
  facets: { models: [], families: [], loras: [], sources: [], kinds: [], total: 0, favorites: 0 },
  tags: [],
  items: [], total: 0, cursor: null, loading: false, done: false,
  filters: {
    library: prefs.library ?? null, q: "", family: null, model: null, lora: null,
    source: null, kind: null, favorite: false, tags: [],
  },
  sort: prefs.sort || "mtime_desc",
  view: prefs.view || "grid",
  tile: prefs.tile || 230,
  focusId: null,          // keyboard focus in the grid
  openId: null,           // image shown in the viewer
  scan: null,             // {scanned,total}
  toasts: [],
  picker: null,           // {mode:'library'|'export', imageId}
  palette: false,
});

export function savePrefs() {
  localStorage.setItem("aig2", JSON.stringify({
    library: S.filters.library, sort: S.sort, view: S.view, tile: S.tile,
  }));
}

let toastId = 0;
export function toast(msg, kind = "info") {
  const id = ++toastId;
  S.toasts.push({ id, msg, kind });
  setTimeout(() => { S.toasts = S.toasts.filter((t) => t.id !== id); }, kind === "error" ? 6000 : 3200);
}
export const fail = (e) => toast(e.message || String(e), "error");

function query(cursor) {
  const f = S.filters, p = new URLSearchParams();
  if (f.library != null) p.set("library_id", f.library);
  for (const k of ["q", "family", "model", "lora", "source", "kind"]) if (f[k]) p.set(k, f[k]);
  if (f.favorite) p.set("favorite", "true");
  for (const t of f.tags) p.append("tag", t);
  p.set("sort", S.sort);
  p.set("limit", "300");
  if (cursor) p.set("cursor", cursor);
  return p.toString();
}

let gen = 0;
export async function reload() {
  const my = ++gen;
  S.loading = true;
  try {
    const r = await api(`/api/images?${query(null)}`);
    if (my !== gen) return;
    S.items = r.items; S.cursor = r.next_cursor; S.done = !r.next_cursor; S.total = r.total ?? r.items.length;
  } catch (e) { if (my === gen) fail(e); }
  finally { if (my === gen) S.loading = false; }
}

export async function loadMore() {
  if (S.loading || S.done || !S.cursor) return;
  const my = gen;
  S.loading = true;
  try {
    const r = await api(`/api/images?${query(S.cursor)}`);
    if (my !== gen) return;
    S.items.push(...r.items); S.cursor = r.next_cursor; S.done = !r.next_cursor;
  } catch (e) { fail(e); }
  finally { if (my === gen) S.loading = false; }
}

// Live refresh: pull the first page again and merge in anything new.
let refreshTimer = null;
export function refreshSoon() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(async () => {
    loadFacets();
    if (S.sort !== "mtime_desc") return reload();
    try {
      const my = gen;
      const r = await api(`/api/images?${query(null)}`);
      if (my !== gen) return;
      const known = new Set(S.items.map((i) => i.id));
      const fresh = r.items.filter((i) => !known.has(i.id));
      if (fresh.length) S.items.unshift(...fresh);
      if (r.total != null) S.total = r.total;
    } catch {}
  }, 500);
}

export async function loadLibraries() { S.libraries = await api("/api/libraries"); }
export async function loadFacets() {
  const q = S.filters.library != null ? `?library_id=${S.filters.library}` : "";
  S.facets = await api(`/api/facets${q}`);
}
export async function loadTags() { S.tags = await api("/api/tags"); }

export function setFilter(key, value) {
  if (key === "tags") {
    S.filters.tags = S.filters.tags.includes(value)
      ? S.filters.tags.filter((t) => t !== value) : [...S.filters.tags, value];
  } else {
    S.filters[key] = S.filters[key] === value ? (key === "favorite" ? false : null) : value;
  }
  if (key === "library") { savePrefs(); loadFacets(); }
  reload();
}
export function clearFilters() {
  Object.assign(S.filters, { q: "", family: null, model: null, lora: null, source: null, kind: null, favorite: false, tags: [] });
  reload();
}
export const activeFilterCount = () => {
  const f = S.filters;
  return ["q", "family", "model", "lora", "source", "kind"].filter((k) => f[k]).length + (f.favorite ? 1 : 0) + f.tags.length;
};

export function removeLocal(id) {
  const i = S.items.findIndex((x) => x.id === id);
  if (i >= 0) { S.items.splice(i, 1); S.total = Math.max(0, S.total - 1); }
  if (S.openId === id) S.openId = S.items[Math.min(i, S.items.length - 1)]?.id ?? null;
  if (S.focusId === id) S.focusId = null;
}

export async function rescan(force = false) {
  const libs = S.filters.library != null ? [S.filters.library] : S.libraries.map((l) => l.id);
  if (!libs.length) return toast("Add a folder first");
  try {
    for (const id of libs) await post(`/api/libraries/${id}/rescan${force ? "?force=true" : ""}`);
    toast(force ? "Reading all metadata again" : "Looking for new files");
  } catch (e) { fail(e); }
}

export async function removeLibrary(lib) {
  if (!confirm(`Remove "${lib.name}" from the gallery?\n\nFiles on disk stay untouched.`)) return;
  try {
    await del(`/api/libraries/${lib.id}`);
    if (S.filters.library === lib.id) S.filters.library = null;
    await loadLibraries(); loadFacets(); reload();
    toast(`Removed "${lib.name}"`);
  } catch (e) { fail(e); }
}

export function connectWS() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === "scan_progress") S.scan = { scanned: m.scanned, total: m.total };
    else if (m.type === "scan_done") {
      S.scan = null;
      toast(`Scan finished: ${m.added} new, ${m.updated} updated, ${m.removed} removed`);
      loadLibraries(); loadFacets(); reload();
    } else if (m.type === "image_added") refreshSoon();
    else if (m.type === "image_removed") { removeLocal(m.image_id); loadFacets(); }
    else if (m.type === "image_changed") window.dispatchEvent(new CustomEvent("aig:changed", { detail: m.image_id }));
    else if (m.type === "family_learned") toast(`Learned a new model family: ${m.base}`);
  };
  ws.onclose = () => setTimeout(connectWS, 2000);
}
