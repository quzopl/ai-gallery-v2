<script>
  import { S, setFilter, toast, fail, removeLocal, loadTags, loadFacets, loadMore, hideFolderOf } from "./store.svelte.js";
  import { api, post, del, thumbUrl, fileUrl } from "./api.js";
  import { familyColor, familyLabel, shortModel, fmtDuration, fmtBytes, fmtDate, sourceLabel } from "./util.js";

  let { onclose } = $props();
  let d = $state(null);
  let showJson = $state(false);
  let zoom = $state(false);
  let tagInput = $state("");
  let auxOpen = $state(false);

  const idx = $derived(S.items.findIndex((x) => x.id === S.openId));
  const item = $derived(S.items[idx]);

  $effect(() => {
    const id = S.openId;
    if (id == null) return;
    showJson = false; zoom = false;
    let live = true;
    api(`/api/images/${id}`).then((r) => { if (live) d = r; }).catch(() => {});
    const on = (e) => { if (e.detail === id) api(`/api/images/${id}`).then((r) => { if (live) d = r; }); };
    window.addEventListener("aig:changed", on);
    return () => { live = false; window.removeEventListener("aig:changed", on); };
  });
  $effect(() => { if (idx >= 0 && idx > S.items.length - 12) loadMore(); });

  export function step(n) {
    const next = S.items[idx + n];
    if (next) { S.openId = next.id; S.focusId = next.id; }
  }
  const cur = $derived(d && d.id === S.openId ? d : null);

  function filterBy(key, value) { setFilter(key, value); onclose(); }

  export async function favorite() {
    if (!item) return;
    const v = !item.is_favorite;
    try {
      await post(`/api/images/${item.id}/favorite`, { value: v });
      item.is_favorite = v ? 1 : 0;
      loadFacets();
    } catch (e) { fail(e); }
  }
  export async function copyPrompt() {
    if (!cur?.prompt) return toast("This file has no prompt");
    await navigator.clipboard.writeText(cur.prompt); toast("Prompt copied");
  }
  async function copy(text, what) { await navigator.clipboard.writeText(text); toast(`${what} copied`); }
  export async function trash() {
    if (!item || !confirm(`Move to trash?\n${item.rel_path}`)) return;
    try { const id = item.id; await del(`/api/images/${id}`); removeLocal(id); toast("Moved to trash"); if (S.openId == null) onclose(); }
    catch (e) { fail(e); }
  }
  async function rename() {
    const curName = item.rel_path.split("/").pop();
    const name = prompt("New file name", curName);
    if (!name || name === curName) return;
    try {
      const r = await post(`/api/images/${item.id}/rename`, { new_name: name });
      item.rel_path = r.new_rel_path; if (d) d.rel_path = r.new_rel_path; toast("Renamed");
    } catch (e) { fail(e); }
  }
  async function hideFolder() {
    if (await hideFolderOf(item)) onclose();
  }
  export function exportIt() { if (item) S.picker = { mode: "export", imageId: item.id }; }
  async function saveTags(tags) {
    try { await post(`/api/images/${item.id}/tags`, { tags }); d.tags = tags; loadTags(); } catch (e) { fail(e); }
  }
  function addTag(e) {
    e.preventDefault();
    const t = tagInput.trim(); tagInput = "";
    if (!t || !cur) return;
    if (cur.tags.includes(t)) return toast("Already tagged");
    saveTags([...cur.tags, t]);
  }
</script>

{#if item}
  <div class="viewer">
    <div class="ambient" style:background-image="url({thumbUrl(item)})"></div>
    <div class="stage" class:zoom>
      {#key item.id}
        {#if item.media_kind === "video"}
          <!-- svelte-ignore a11y_media_has_caption -->
          <video class="media" src={fileUrl(item)} poster={thumbUrl(item)} controls autoplay loop playsinline style:view-transition-name="hero"></video>
        {:else}
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
          <img class="media" src={fileUrl(item)} alt={item.rel_path} style:view-transition-name="hero"
            style:background-image="url({thumbUrl(item)})" onclick={() => (zoom = !zoom)} />
        {/if}
      {/key}
      <button class="nav prev" onclick={() => step(-1)} disabled={idx <= 0} aria-label="Previous">‹</button>
      <button class="nav next" onclick={() => step(1)} disabled={idx >= S.items.length - 1} aria-label="Next">›</button>
      <button class="close btn icon" onclick={onclose} aria-label="Close">✕</button>
      <span class="pos">{idx + 1} of {S.total}</span>
    </div>

    <aside class="panel glass">
      <header>
        <button class="fam" style:--fam={familyColor(item.family)} onclick={() => filterBy("family", item.family ?? "__none__")} title="Show everything made with this family">
          <i></i>{familyLabel(item.family)}
        </button>
        <div class="acts">
          <button class="btn icon" class:fav={item.is_favorite} onclick={favorite} title="Favorite (F)">{item.is_favorite ? "★" : "☆"}</button>
          <button class="btn icon" onclick={exportIt} title="Copy to a folder (Ctrl+E)">⇪</button>
          <button class="btn icon" onclick={rename} title="Rename">✎</button>
          <button class="btn icon" onclick={hideFolder} title="Hide this folder from the gallery">⊘</button>
          <button class="btn icon danger" onclick={trash} title="Move to trash (Del)">🗑</button>
        </div>
      </header>

      {#if cur}
        <div class="body">
          <section>
            <div class="lab">Prompt
              {#if cur.prompt}<button onclick={copyPrompt}>Copy</button>{/if}
              {#if cur.prompt_json}<button onclick={() => (showJson = !showJson)}>{showJson ? "Text" : "JSON"}</button>{/if}
              {#if cur.prompt_json && showJson}<button onclick={() => copy(cur.prompt_json, "JSON")}>Copy JSON</button>{/if}
            </div>
            {#if showJson && cur.prompt_json}<pre>{cur.prompt_json}</pre>
            {:else if cur.prompt}<p class="prompt">{cur.prompt}</p>
            {:else}<p class="none">No prompt was found in this file.</p>{/if}
          </section>

          {#if cur.negative}
            <section><div class="lab">Negative prompt <button onclick={() => copy(cur.negative, "Negative prompt")}>Copy</button></div><p class="prompt neg">{cur.negative}</p></section>
          {/if}

          <section>
            <div class="lab">Model</div>
            {#if cur.model_name}
              <button class="chip wide" title={cur.model_name} onclick={() => filterBy("model", cur.model_name)}>{shortModel(cur.model_name)}</button>
            {:else}<p class="none">No model was found in this file.</p>{/if}
          </section>

          {#if cur.loras.length}
            <section>
              <div class="lab">LoRA</div>
              {#each cur.loras as l (l.name)}
                <button class="lora" title={l.name} onclick={() => filterBy("lora", l.name)}>
                  <span>{shortModel(l.name)}</span>
                  {#if l.strength != null}<b>{(+l.strength).toFixed(2)}</b>{/if}
                  <i style:width="{Math.min(100, Math.abs(l.strength ?? 1) * 66)}%"></i>
                </button>
              {/each}
            </section>
          {/if}

          <section class="grid">
            {#if cur.sampler}<div><span>Sampler</span>{cur.sampler}</div>{/if}
            {#if cur.steps != null}<div><span>Steps</span>{cur.steps}</div>{/if}
            {#if cur.cfg != null}<div><span>CFG</span>{cur.cfg}</div>{/if}
            {#if cur.seed != null}<div><span>Seed</span><button class="seed" onclick={() => copy(String(cur.seed), "Seed")}>{cur.seed}</button></div>{/if}
            {#if cur.width}<div><span>Size</span>{cur.width} × {cur.height}</div>{/if}
            {#if cur.duration}<div><span>Length</span>{fmtDuration(cur.duration)}{cur.fps ? `, ${Math.round(cur.fps)} fps` : ""}</div>{/if}
            <div><span>Made with</span><button class="seed" onclick={() => filterBy("source", cur.source_kind ?? "__none__")}>{sourceLabel(cur.source_kind)}</button></div>
            <div><span>File size</span>{fmtBytes(cur.size_bytes)}</div>
            <div class="full"><span>Saved</span>{fmtDate(cur.mtime)}</div>
            <div class="full"><span>File</span><a href={fileUrl(item)} target="_blank" rel="noreferrer">{cur.rel_path}</a></div>
          </section>

          {#if cur.aux_models.length}
            <section>
              <button class="lab toggle" onclick={() => (auxOpen = !auxOpen)}>Other models in this workflow ({cur.aux_models.length}) <span>{auxOpen ? "–" : "+"}</span></button>
              {#if auxOpen}
                {#each cur.aux_models as a (a.name)}
                  <div class="aux"><span>{a.role.replace("_", " ")}</span>{shortModel(a.name)}</div>
                {/each}
              {/if}
            </section>
          {/if}

          <section>
            <div class="lab">Tags</div>
            <div class="tags">
              {#each cur.tags as t (t)}
                <span class="chip">{t}<button onclick={() => saveTags(cur.tags.filter((x) => x !== t))} aria-label="Remove tag">×</button></span>
              {/each}
            </div>
            <form onsubmit={addTag}><input class="field" placeholder="Add a tag and press Enter" bind:value={tagInput} list="alltags" /></form>
            <datalist id="alltags">{#each S.tags as t (t.id)}<option value={t.name}></option>{/each}</datalist>
          </section>
        </div>
      {/if}
    </aside>
  </div>
{/if}

<style>
  .viewer { position: fixed; inset: 0; z-index: 30; display: flex; background: #000; animation: fade .2s both; }
  @keyframes fade { from { opacity: 0; } }
  .ambient {
    position: absolute; inset: -12%; background-size: cover; background-position: center;
    filter: blur(90px) saturate(1.5) brightness(.5); opacity: .85; transition: background-image .5s;
  }
  .stage { position: relative; flex: 1; min-width: 0; display: flex; align-items: center; justify-content: center; padding: 28px; }
  .media {
    max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 6px;
    box-shadow: 0 30px 90px rgba(0,0,0,.6); background-size: contain; background-position: center; background-repeat: no-repeat;
  }
  img.media { cursor: zoom-in; }
  .stage.zoom { overflow: auto; align-items: flex-start; justify-content: flex-start; }
  .stage.zoom img.media { max-width: none; max-height: none; cursor: zoom-out; }
  /* zoomed: the stage scrolls, so overlays would sit on top of the picture */
  .stage.zoom .pos, .stage.zoom .nav { display: none; }
  .nav {
    position: absolute; top: 50%; width: 46px; height: 76px; margin-top: -38px; border-radius: 12px;
    font-size: 34px; line-height: 1; color: #fff; background: rgba(0,0,0,.35); backdrop-filter: blur(10px);
    opacity: 0; transition: opacity .2s, background .2s;
  }
  .stage:hover .nav { opacity: 1; }
  .nav:hover { background: rgba(255,255,255,.16); }
  .nav:disabled { display: none; }
  .prev { left: 14px; } .next { right: 14px; }
  .close { position: absolute; top: 14px; left: 14px; background: rgba(0,0,0,.4); backdrop-filter: blur(10px); }
  .pos { position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); font-size: 12px; color: rgba(255,255,255,.55); }

  .panel {
    position: relative; width: 400px; flex: none; margin: 12px 12px 12px 0; border-radius: var(--r-lg);
    display: flex; flex-direction: column; overflow: hidden; animation: slide .35s var(--ease) both;
  }
  @keyframes slide { from { transform: translateX(24px); opacity: 0; } }
  header { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 14px 14px 12px 18px; border-bottom: 1px solid var(--line); }
  .fam { display: flex; align-items: center; gap: 9px; font-size: 19px; font-weight: 650; letter-spacing: -0.015em; min-width: 0; }
  .fam i { width: 11px; height: 11px; border-radius: 50%; background: var(--fam); box-shadow: 0 0 16px var(--fam); flex: none; }
  .fam:hover { text-decoration: underline; text-underline-offset: 4px; }
  .acts { display: flex; gap: 6px; }
  .fav { color: var(--gold); }
  .body { overflow-y: auto; padding: 4px 18px 22px; }
  section { padding: 14px 0; border-bottom: 1px solid var(--line); }
  section:last-child { border: 0; }
  .lab { display: flex; align-items: center; gap: 10px; font-size: 12px; font-weight: 600; color: var(--faint); margin-bottom: 7px; }
  .lab button { color: var(--dim); font-weight: 500; padding: 1px 7px; border-radius: 6px; border: 1px solid var(--line); }
  .lab button:hover { color: #fff; border-color: rgba(255,255,255,.3); }
  .lab.toggle { width: 100%; justify-content: space-between; margin: 0; }
  .lab.toggle:hover { color: var(--text); }
  .prompt { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14.5px; line-height: 1.55; user-select: text; }
  .prompt.neg { color: var(--dim); }
  .none { margin: 0; color: var(--faint); }
  pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; color: var(--dim); max-height: 340px; overflow: auto; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 11px; border-radius: 20px; background: var(--raise); border: 1px solid var(--line); max-width: 100%; }
  .chip.wide { border-radius: 9px; padding: 7px 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; text-align: left; }
  button.chip:hover { background: var(--raise-2); }
  .chip button { color: var(--faint); } .chip button:hover { color: var(--danger); }
  .lora { position: relative; display: flex; width: 100%; justify-content: space-between; gap: 10px; padding: 7px 11px; margin-bottom: 5px; border-radius: 9px; background: var(--raise); overflow: hidden; text-align: left; }
  .lora span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lora b { font-weight: 500; color: var(--dim); }
  .lora i { position: absolute; left: 0; bottom: 0; height: 2px; background: rgba(255,255,255,.55); }
  .lora:hover { background: var(--raise-2); }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
  .grid div { min-width: 0; overflow-wrap: anywhere; }
  .grid .full { grid-column: 1 / -1; }
  .grid span { display: block; font-size: 12px; color: var(--faint); margin-bottom: 1px; }
  .grid a { color: var(--text); text-decoration-color: var(--faint); text-underline-offset: 3px; }
  .seed { text-align: left; } .seed:hover { text-decoration: underline; text-underline-offset: 3px; }
  .aux { display: flex; gap: 10px; padding: 5px 0 0; color: var(--dim); overflow-wrap: anywhere; }
  .aux span { flex: none; width: 92px; color: var(--faint); }
  .tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  @media (max-width: 900px) {
    .viewer { flex-direction: column; }
    .panel { width: auto; margin: 0 8px 8px; max-height: 46vh; }
    .stage { padding: 10px; min-height: 0; }
  }
</style>
