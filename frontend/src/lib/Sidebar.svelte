<script>
  import { S, setFilter, removeLibrary, loadTags, toast, fail } from "./store.svelte.js";
  import { del } from "./api.js";
  import { familyColor, familyLabel, shortModel, fmtCount, sourceLabel } from "./util.js";

  let open = $state({ family: true, model: false, lora: false, source: false, tag: true });
  let find = $state({ model: "", lora: "" });
  const pick = (list, q, n = 60) => {
    const s = q.trim().toLowerCase();
    return (s ? list.filter((x) => (x.name || "").toLowerCase().includes(s)) : list).slice(0, n);
  };

  async function dropTag(t) {
    if (!confirm(`Delete tag "${t.name}" from all images?`)) return;
    try {
      await del(`/api/tags/${t.id}`);
      S.filters.tags = S.filters.tags.filter((x) => x !== t.name);
      await loadTags(); toast(`Deleted tag "${t.name}"`);
    } catch (e) { fail(e); }
  }
</script>

<aside>
  <section>
    <h3>Folders</h3>
    <button class="row" class:on={S.filters.library == null} onclick={() => S.filters.library != null && setFilter("library", S.filters.library)}>
      <span class="name">All folders</span><span class="n">{fmtCount(S.libraries.reduce((a, l) => a + l.image_count, 0))}</span>
    </button>
    {#each S.libraries as lib (lib.id)}
      <div class="row-wrap">
        <button class="row" class:on={S.filters.library === lib.id} title={lib.path}
          onclick={() => S.filters.library !== lib.id && setFilter("library", lib.id)}>
          <span class="name">{lib.name}</span><span class="n">{fmtCount(lib.image_count)}</span>
        </button>
        <button class="x" title="Remove folder from the gallery" onclick={() => removeLibrary(lib)}>×</button>
      </div>
    {/each}
    <button class="row add" onclick={() => (S.picker = { mode: "library" })}>+ Add folder</button>
  </section>

  <section>
    <h3>Show</h3>
    <div class="seg">
      <button class:on={!S.filters.kind} onclick={() => S.filters.kind && setFilter("kind", S.filters.kind)}>All</button>
      <button class:on={S.filters.kind === "image"} onclick={() => setFilter("kind", "image")}>Images</button>
      <button class:on={S.filters.kind === "video"} onclick={() => setFilter("kind", "video")}>Videos</button>
    </div>
    <button class="row" class:on={S.filters.favorite} onclick={() => setFilter("favorite", true)}>
      <span class="name"><b class="gold">★</b> Favorites</span><span class="n">{fmtCount(S.facets.favorites)}</span>
    </button>
  </section>

  <section>
    <button class="head" onclick={() => (open.family = !open.family)}><h3>Model family</h3><span>{open.family ? "–" : "+"}</span></button>
    {#if open.family}
      {#each S.facets.families as f (f.name)}
        <button class="row" class:on={S.filters.family === (f.name ?? "__none__")} onclick={() => setFilter("family", f.name ?? "__none__")}>
          <span class="name"><i style:background={familyColor(f.name)}></i>{familyLabel(f.name)}</span><span class="n">{fmtCount(f.count)}</span>
        </button>
      {/each}
    {/if}
  </section>

  <section>
    <button class="head" onclick={() => (open.model = !open.model)}><h3>Model file</h3><span>{open.model ? "–" : "+"}</span></button>
    {#if open.model}
      <input class="field mini" placeholder="Find a model" bind:value={find.model} />
      {#each pick(S.facets.models.filter((m) => m.name), find.model) as m (m.name)}
        <button class="row" class:on={S.filters.model === m.name} title={m.name} onclick={() => setFilter("model", m.name)}>
          <span class="name">{shortModel(m.name)}</span><span class="n">{fmtCount(m.count)}</span>
        </button>
      {/each}
    {/if}
  </section>

  <section>
    <button class="head" onclick={() => (open.lora = !open.lora)}><h3>LoRA</h3><span>{open.lora ? "–" : "+"}</span></button>
    {#if open.lora}
      <input class="field mini" placeholder="Find a LoRA" bind:value={find.lora} />
      {#each pick(S.facets.loras, find.lora) as l (l.name)}
        <button class="row" class:on={S.filters.lora === l.name} title={l.name} onclick={() => setFilter("lora", l.name)}>
          <span class="name">{shortModel(l.name)}</span><span class="n">{fmtCount(l.count)}</span>
        </button>
      {/each}
    {/if}
  </section>

  <section>
    <button class="head" onclick={() => (open.source = !open.source)}><h3>Made with</h3><span>{open.source ? "–" : "+"}</span></button>
    {#if open.source}
      {#each S.facets.sources as s (s.name)}
        <button class="row" class:on={S.filters.source === (s.name ?? "__none__")} onclick={() => setFilter("source", s.name ?? "__none__")}>
          <span class="name">{sourceLabel(s.name)}</span><span class="n">{fmtCount(s.count)}</span>
        </button>
      {/each}
    {/if}
  </section>

  {#if S.tags.length}
    <section>
      <button class="head" onclick={() => (open.tag = !open.tag)}><h3>Tags</h3><span>{open.tag ? "–" : "+"}</span></button>
      {#if open.tag}
        <div class="tags">
          {#each S.tags as t (t.id)}
            <span class="tag" class:on={S.filters.tags.includes(t.name)}>
              <button onclick={() => setFilter("tags", t.name)}>{t.name} <em>{t.count}</em></button>
              <button class="tx" title="Delete tag everywhere" onclick={() => dropTag(t)}>×</button>
            </span>
          {/each}
        </div>
      {/if}
    </section>
  {/if}
</aside>

<style>
  aside { width: 264px; flex: none; height: 100%; overflow-y: auto; padding: 6px 10px 30px; background: var(--rail); border-right: 1px solid var(--line); }
  section { padding: 12px 0 10px; border-bottom: 1px solid var(--line); }
  section:last-child { border: 0; }
  h3 { margin: 0; padding: 0 8px 6px; font-size: 12px; font-weight: 600; color: var(--faint); letter-spacing: .02em; }
  .head { display: flex; width: 100%; justify-content: space-between; align-items: baseline; color: var(--faint); padding-right: 8px; }
  .head:hover h3 { color: var(--text); }
  .row-wrap { position: relative; }
  .row {
    display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 10px;
    padding: 5px 8px; border-radius: 7px; color: var(--dim); text-align: left; transition: background .12s, color .12s;
  }
  .row:hover { background: var(--raise); color: var(--text); }
  .row.on { background: var(--raise-2); color: #fff; font-weight: 550; }
  .row.add { color: var(--faint); }
  .name { display: flex; align-items: center; gap: 8px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .name i { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .n { color: var(--faint); font-size: 12px; flex: none; font-variant-numeric: tabular-nums; }
  .gold { color: var(--gold); font-weight: 400; }
  .x { position: absolute; right: 2px; top: 3px; width: 22px; height: 22px; border-radius: 6px; color: var(--faint); background: var(--rail); opacity: 0; }
  .row-wrap:hover .x { opacity: 1; }
  .x:hover { color: var(--danger); }
  .seg { display: flex; margin: 0 4px 6px; padding: 3px; border-radius: 9px; background: rgba(0,0,0,.4); border: 1px solid var(--line); }
  .seg button { flex: 1; padding: 4px 0; border-radius: 6px; color: var(--dim); font-size: 13px; }
  .seg button.on { background: var(--raise-2); color: #fff; }
  .seg em, .tag em { font-style: normal; color: var(--faint); font-size: 11px; }
  .mini { height: 28px; margin: 0 4px 6px; width: calc(100% - 8px); font-size: 13px; }
  .tags { display: flex; flex-wrap: wrap; gap: 5px; padding: 0 6px; }
  .tag { display: inline-flex; border-radius: 20px; border: 1px solid var(--line); color: var(--dim); overflow: hidden; }
  .tag > button:first-child { padding: 2px 4px 2px 10px; }
  .tag .tx { padding: 0 8px 0 3px; color: var(--faint); }
  .tag .tx:hover { color: var(--danger); }
  .tag.on { background: var(--text); color: #0a0a0c; border-color: transparent; }
</style>
