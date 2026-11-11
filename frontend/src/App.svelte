<script>
  import { flushSync } from "svelte";
  import { S, reload, loadLibraries, loadFacets, loadTags, connectWS, setFilter, clearFilters,
           activeFilterCount, rescan, savePrefs } from "./lib/store.svelte.js";
  import { familyLabel, shortModel, fmtCount, sourceLabel } from "./lib/util.js";
  import Grid from "./lib/Grid.svelte";
  import Sidebar from "./lib/Sidebar.svelte";
  import Viewer from "./lib/Viewer.svelte";
  import FolderPicker from "./lib/FolderPicker.svelte";
  import Palette from "./lib/Palette.svelte";

  let grid = $state(null), viewer = $state(null), search = $state(null);
  let railOpen = $state(window.innerWidth > 900);
  let qTimer;

  loadLibraries().then(() => {
    if (S.filters.library != null && !S.libraries.some((l) => l.id === S.filters.library)) S.filters.library = null;
    loadFacets(); reload();
  });
  loadTags();
  connectWS();

  function onSearch() {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => { reload(); grid?.toTop(); }, 220);
  }

  // Tile → full screen as one continuous move (View Transitions), plain swap elsewhere.
  function transition(fn, tile) {
    if (!document.startViewTransition || matchMedia("(prefers-reduced-motion: reduce)").matches) return fn();
    if (tile) tile.style.viewTransitionName = "hero";
    const t = document.startViewTransition(() => { if (tile) tile.style.viewTransitionName = ""; flushSync(fn); });
    return t.finished;
  }
  function open(id, tile) {
    S.focusId = id;
    transition(() => (S.openId = id), tile);
  }
  function close() {
    const id = S.openId;
    grid?.reveal(id);
    transition(() => {
      S.openId = null;
      const tile = document.querySelector(`.tile[data-id="${id}"]`);
      if (tile) { tile.style.viewTransitionName = "hero"; requestAnimationFrame(() => (tile.style.viewTransitionName = "")); }
    });
  }

  function move(n) {
    if (!S.items.length) return;
    let i = S.items.findIndex((x) => x.id === S.focusId);
    i = i < 0 ? 0 : Math.max(0, Math.min(S.items.length - 1, i + n));
    S.focusId = S.items[i].id;
    grid?.reveal(S.focusId);
  }

  function onkey(e) {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); S.palette = !S.palette; return; }
    if (S.palette || S.picker) { if (e.key === "Escape") { S.palette = false; S.picker = null; } return; }
    const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
    if (typing) { if (e.key === "Escape") document.activeElement.blur(); return; }
    if (e.key === "/") { e.preventDefault(); search?.focus(); return; }

    if (S.openId != null) {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowLeft") viewer?.step(-1);
      else if (e.key === "ArrowRight") viewer?.step(1);
      else if (e.key.toLowerCase() === "f" && !mod) viewer?.favorite();
      else if (e.key === "Delete") viewer?.trash();
      else if (mod && e.key.toLowerCase() === "e") { e.preventDefault(); viewer?.exportIt(); }
      else if (mod && e.key.toLowerCase() === "c" && !String(getSelection())) viewer?.copyPrompt();
      return;
    }
    const cols = grid?.cols() ?? 1;
    const steps = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -cols, ArrowDown: cols, PageUp: -cols * 4, PageDown: cols * 4 };
    if (e.key in steps) { e.preventDefault(); move(steps[e.key]); }
    else if (e.key === "Home") { e.preventDefault(); S.focusId = S.items[0]?.id; grid?.toTop(); }
    else if (e.key === "Enter" && S.focusId != null) open(S.focusId, document.querySelector(`.tile[data-id="${S.focusId}"]`));
    else if (e.key === "Escape") S.focusId = null;
    else if (mod && (e.key === "-" || e.key === "=")) { e.preventDefault(); S.tile = Math.max(120, Math.min(480, S.tile + (e.key === "-" ? -30 : 30))); savePrefs(); }
  }

  const chips = $derived.by(() => {
    const f = S.filters, out = [];
    if (f.kind) out.push({ k: "kind", t: f.kind === "video" ? "Videos" : "Images" });
    if (f.favorite) out.push({ k: "favorite", t: "Favorites" });
    if (f.family) out.push({ k: "family", t: familyLabel(f.family === "__none__" ? null : f.family) });
    if (f.model) out.push({ k: "model", t: shortModel(f.model) });
    if (f.lora) out.push({ k: "lora", t: `LoRA ${shortModel(f.lora)}` });
    if (f.source) out.push({ k: "source", t: sourceLabel(f.source === "__none__" ? null : f.source) });
    for (const t of f.tags) out.push({ k: "tags", v: t, t: `#${t}` });
    return out;
  });
</script>

<svelte:window onkeydown={onkey} />

<div class="app">
  <header class="top">
    <button class="btn icon" onclick={() => (railOpen = !railOpen)} title="Filters" aria-label="Toggle filters">☰</button>
    <div class="brand">AI Gallery</div>
    <div class="search">
      <input bind:this={search} class="field" placeholder="Search prompts and models" bind:value={S.filters.q} oninput={onSearch} />
      <button class="hint" onclick={() => (S.palette = true)} title="Command palette"><kbd>Ctrl K</kbd></button>
    </div>
    <div class="tools">
      <select class="btn" bind:value={S.sort} onchange={() => { savePrefs(); reload(); grid?.toTop(); }} aria-label="Order">
        <option value="mtime_desc">Newest first</option>
        <option value="mtime_asc">Oldest first</option>
      </select>
      <div class="seg">
        <button class:on={S.view === "grid"} onclick={() => { S.view = "grid"; savePrefs(); }}>Grid</button>
        <button class:on={S.view === "masonry"} onclick={() => { S.view = "masonry"; savePrefs(); }}>Masonry</button>
      </div>
      <input class="size" type="range" min="120" max="480" step="10" bind:value={S.tile} onchange={savePrefs} aria-label="Tile size" title="Tile size" />
      <button class="btn icon" onclick={(e) => rescan(e.shiftKey)} title="Look for new files (Shift+click: read all metadata again)">⟳</button>
    </div>
    {#if S.scan}
      <div class="progress"><i style:width="{(S.scan.scanned / Math.max(1, S.scan.total)) * 100}%"></i></div>
    {/if}
  </header>

  <div class="main">
    {#if railOpen}<Sidebar />{/if}
    <div class="content">
      <div class="status">
        <span class="count">{fmtCount(S.total)} {S.total === 1 ? "file" : "files"}</span>
        {#if S.scan}<span class="scan">Reading {fmtCount(S.scan.scanned)} of {fmtCount(S.scan.total)}</span>{/if}
        {#each chips as c (c.k + (c.v ?? ""))}
          <button class="chip" onclick={() => setFilter(c.k, c.v ?? S.filters[c.k])}>{c.t}<span>×</span></button>
        {/each}
        {#if activeFilterCount() > 1}<button class="clear" onclick={clearFilters}>Clear all</button>{/if}
      </div>
      <div class="gridwrap"><Grid bind:this={grid} onopen={open} /></div>
    </div>
  </div>

  {#if S.openId != null}<Viewer bind:this={viewer} onclose={close} />{/if}
  {#if S.picker}<FolderPicker />{/if}
  {#if S.palette}<Palette />{/if}

  <div class="toasts" aria-live="polite">
    {#each S.toasts as t (t.id)}<div class="toast glass" class:error={t.kind === "error"}>{t.msg}</div>{/each}
  </div>
</div>

<style>
  .app { height: 100%; display: flex; flex-direction: column; }
  .top { position: relative; display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-bottom: 1px solid var(--line); background: var(--rail); }
  .brand { font-size: 17px; font-weight: 700; letter-spacing: -0.02em; margin-right: 6px; white-space: nowrap; }
  .search { position: relative; flex: 1; max-width: 560px; }
  .search .field { padding-right: 70px; }
  .hint { position: absolute; right: 8px; top: 7px; }
  .tools { display: flex; align-items: center; gap: 8px; margin-left: auto; }
  select.btn { appearance: none; padding-right: 13px; }
  select.btn option { background: #16161a; }
  .seg { display: flex; padding: 3px; border-radius: var(--r); background: rgba(0,0,0,.4); border: 1px solid var(--line); }
  .seg button { padding: 3px 11px; border-radius: 7px; color: var(--dim); transition: background .15s, color .15s; }
  .seg button.on { background: var(--raise-2); color: #fff; }
  .size { width: 96px; accent-color: #fff; }
  .progress { position: absolute; left: 0; right: 0; bottom: -1px; height: 2px; }
  .progress i { display: block; height: 100%; background: #fff; transition: width .3s; }
  .main { flex: 1; min-height: 0; display: flex; }
  .content { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .status { display: flex; align-items: center; flex-wrap: wrap; gap: 7px; padding: 10px 16px; min-height: 46px; }
  .count { color: var(--dim); margin-right: 6px; }
  .scan { color: var(--faint); margin-right: 6px; }
  .chip { display: inline-flex; gap: 7px; align-items: center; padding: 3px 9px 3px 11px; border-radius: 20px; background: var(--text); color: #0a0a0c; font-weight: 550; animation: chip .22s var(--ease) both; }
  @keyframes chip { from { transform: scale(.85); opacity: 0; } }
  .chip span { opacity: .5; } .chip:hover span { opacity: 1; }
  .clear { color: var(--dim); text-decoration: underline; text-underline-offset: 3px; }
  .gridwrap { flex: 1; min-height: 0; }
  .toasts { position: fixed; z-index: 80; bottom: 18px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; gap: 8px; align-items: center; pointer-events: none; }
  .toast { padding: 9px 16px; border-radius: 30px; max-width: 80vw; overflow-wrap: anywhere; animation: up .3s var(--ease) both; }
  .toast.error { border-color: rgba(255,107,107,.55); color: #ffc4c4; }
  @keyframes up { from { transform: translateY(12px); opacity: 0; } }
  @media (max-width: 900px) {
    .brand, .size, .seg, select.btn { display: none; }
    .main :global(aside) { position: absolute; z-index: 20; height: calc(100% - 55px); }
  }
</style>
