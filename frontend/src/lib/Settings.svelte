<script>
  import { S, showFolderAgain, removeLibrary, rescan } from "./store.svelte.js";
  import { fmtCount } from "./util.js";
  const close = () => (S.settings = false);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="veil" onclick={(e) => e.target === e.currentTarget && close()}>
  <div class="box glass" role="dialog" aria-label="Settings">
    <header>
      <h2>Settings</h2>
      <button class="btn icon" onclick={close} aria-label="Close">✕</button>
    </header>
    <div class="body">
      <section>
        <h3>Hidden folders</h3>
        <p>Files in these folders, and in folders inside them, stay on disk but do not show in the gallery, its counts or its filters.</p>
        {#each S.hidden as h (h.id)}
          <div class="row">
            <div class="path" title={h.path}>{h.path}<span>{fmtCount(h.count)} {h.count === 1 ? "file" : "files"}</span></div>
            <button class="btn" onclick={() => showFolderAgain(h)}>Show again</button>
          </div>
        {:else}
          <div class="none">No folder is hidden. Open a file and press ⊘ to hide the folder it is in.</div>
        {/each}
      </section>
      <section>
        <h3>Folders in the gallery</h3>
        {#each S.libraries as lib (lib.id)}
          <div class="row">
            <div class="path" title={lib.path}>{lib.path}<span>{lib.name}, {fmtCount(lib.image_count)} shown</span></div>
            <button class="btn danger" onclick={() => removeLibrary(lib)}>Remove</button>
          </div>
        {:else}
          <div class="none">No folders yet.</div>
        {/each}
        <div class="acts">
          <button class="btn" onclick={() => { close(); S.picker = { mode: "library" }; }}>Add folder</button>
          <button class="btn" onclick={() => rescan(false)}>Look for new files</button>
          <button class="btn" onclick={() => rescan(true)}>Read all metadata again</button>
        </div>
      </section>
    </div>
  </div>
</div>

<style>
  .veil { position: fixed; inset: 0; z-index: 55; background: rgba(0,0,0,.6); display: grid; place-items: center; animation: f .15s both; }
  @keyframes f { from { opacity: 0; } }
  .box { background: rgba(18,18,22,.94); width: min(720px, 94vw); max-height: 86vh; border-radius: var(--r-lg); display: flex; flex-direction: column; animation: pop .28s var(--ease) both; }
  @keyframes pop { from { transform: translateY(14px) scale(.98); opacity: 0; } }
  header { display: flex; justify-content: space-between; align-items: center; padding: 14px 14px 10px 22px; border-bottom: 1px solid var(--line); }
  h2 { margin: 0; font-size: 18px; font-weight: 650; letter-spacing: -0.01em; }
  .body { overflow-y: auto; padding: 4px 22px 20px; }
  section { padding: 16px 0; border-bottom: 1px solid var(--line); }
  section:last-child { border: 0; padding-bottom: 0; }
  h3 { margin: 0 0 4px; font-size: 15px; font-weight: 600; }
  p { margin: 0 0 12px; color: var(--dim); max-width: 62ch; }
  .row { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
  .path { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .path span { display: block; color: var(--faint); font-size: 12px; }
  .none { color: var(--faint); padding: 6px 0; }
  .acts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
</style>
