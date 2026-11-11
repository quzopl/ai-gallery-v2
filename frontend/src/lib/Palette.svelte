<script>
  import { S, setFilter, clearFilters, rescan, savePrefs, reload } from "./store.svelte.js";
  import { familyLabel, shortModel } from "./util.js";

  let q = $state("");
  let sel = $state(0);
  let input = $state(null);
  $effect(() => { input?.focus(); });
  const close = () => (S.palette = false);

  const all = $derived([
    { t: "Add folder", k: "Action", run: () => (S.picker = { mode: "library" }) },
    { t: "Look for new files", k: "Action", run: () => rescan(false) },
    { t: "Read all metadata again", k: "Action", run: () => rescan(true) },
    { t: "Clear all filters", k: "Action", run: clearFilters },
    { t: S.view === "grid" ? "Switch to masonry layout" : "Switch to square grid", k: "Action", run: () => { S.view = S.view === "grid" ? "masonry" : "grid"; savePrefs(); } },
    { t: "Show favorites", k: "Filter", run: () => setFilter("favorite", true) },
    { t: "Show only videos", k: "Filter", run: () => setFilter("kind", "video") },
    { t: "Show only images", k: "Filter", run: () => setFilter("kind", "image") },
    ...S.facets.families.map((f) => ({ t: familyLabel(f.name), k: "Family", n: f.count, run: () => setFilter("family", f.name ?? "__none__") })),
    ...S.facets.models.filter((m) => m.name).map((m) => ({ t: shortModel(m.name), k: "Model", n: m.count, run: () => setFilter("model", m.name) })),
    ...S.facets.loras.map((l) => ({ t: shortModel(l.name), k: "LoRA", n: l.count, run: () => setFilter("lora", l.name) })),
    ...S.tags.map((t) => ({ t: t.name, k: "Tag", n: t.count, run: () => setFilter("tags", t.name) })),
  ]);
  const hits = $derived.by(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return all.filter((a) => words.every((w) => `${a.t} ${a.k}`.toLowerCase().includes(w))).slice(0, 40);
  });
  $effect(() => { q; sel = 0; });

  function key(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(hits.length - 1, sel + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); }
    else if (e.key === "Enter") { e.preventDefault(); pick(hits[sel]); }
    else if (e.key === "Escape") { e.stopPropagation(); close(); }
  }
  function pick(h) {
    if (h) { h.run(); close(); }
    else if (q.trim()) { S.filters.q = q.trim(); reload(); close(); }
  }
  function scrollSel(node, on) {
    const upd = (v) => v && node.scrollIntoView({ block: "nearest" });
    upd(on);
    return { update: upd };
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="veil" onclick={(e) => e.target === e.currentTarget && close()}>
  <div class="box glass">
    <input bind:this={input} bind:value={q} onkeydown={key} placeholder="Type a model, LoRA, tag or action" />
    <ul>
      {#each hits as h, i (i)}
        <li>
          <button class:sel={i === sel} use:scrollSel={i === sel} onmousemove={() => (sel = i)} onclick={() => pick(h)}>
            <span class="k">{h.k}</span><span class="t">{h.t}</span>{#if h.n != null}<span class="n">{h.n}</span>{/if}
          </button>
        </li>
      {:else}
        <li class="none">Nothing found. Press Enter to search prompts for “{q}”.</li>
      {/each}
    </ul>
  </div>
</div>

<style>
  .veil { position: fixed; inset: 0; z-index: 60; background: rgba(0,0,0,.5); display: flex; justify-content: center; align-items: flex-start; padding-top: 14vh; }
  .box { background: rgba(18,18,22,.92); width: min(620px, 94vw); border-radius: var(--r-lg); overflow: hidden; animation: pop .22s var(--ease) both; box-shadow: 0 40px 120px rgba(0,0,0,.7); }
  @keyframes pop { from { transform: translateY(-10px) scale(.98); opacity: 0; } }
  input { width: 100%; padding: 17px 20px; font-size: 17px; background: none; border: 0; border-bottom: 1px solid var(--line); outline: none; }
  ul { margin: 0; padding: 6px; list-style: none; max-height: 52vh; overflow-y: auto; }
  li button { display: flex; width: 100%; gap: 12px; align-items: baseline; padding: 8px 12px; border-radius: 8px; text-align: left; }
  li button.sel { background: var(--raise-2); }
  .k { width: 52px; flex: none; font-size: 12px; color: var(--faint); }
  .t { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .n { color: var(--faint); font-size: 12px; }
  .none { padding: 14px; color: var(--dim); }
</style>
