<script>
  import { S, toast, fail, loadLibraries, loadFacets, reload } from "./store.svelte.js";
  import { api, post } from "./api.js";

  const mode = $derived(S.picker.mode);
  let path = $state(null), parent = $state(null), dirs = $state([]), isRoots = $state(false);
  let name = $state("");
  let busy = $state(false);

  async function go(p) {
    try {
      const r = await api(p ? `/api/browse?path=${encodeURIComponent(p)}` : "/api/browse");
      path = r.path; parent = r.parent; dirs = r.dirs; isRoots = !!r.is_roots;
      return true;
    } catch (e) { fail(e); return false; }
  }
  $effect(() => {
    const start = mode === "export" ? localStorage.getItem("aig2.exportDir") : null;
    go(start).then((ok) => { if (!ok && start) go(null); });
  });

  const close = () => (S.picker = null);

  async function mkdir() {
    const n = prompt("New folder name");
    if (!n?.trim()) return;
    try { const r = await post("/api/browse/mkdir", { parent: path, name: n.trim() }); await go(r.path); toast("Folder created"); }
    catch (e) { fail(e); }
  }
  async function confirmPick() {
    busy = true;
    try {
      if (mode === "library") {
        await post("/api/libraries", { path, name: name.trim() || null });
        toast("Folder added. Reading files now");
        await loadLibraries(); loadFacets(); reload();
      } else {
        const r = await post(`/api/images/${S.picker.imageId}/export`, { to_dir: path });
        localStorage.setItem("aig2.exportDir", path);
        toast(`Copied to ${r.path}`);
      }
      close();
    } catch (e) { fail(e); }
    finally { busy = false; }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="veil" onclick={(e) => e.target === e.currentTarget && close()}>
  <div class="box glass" role="dialog" aria-label="Choose a folder">
    <header>
      <h2>{mode === "library" ? "Add a folder to the gallery" : "Copy this file to a folder"}</h2>
      <button class="btn icon" onclick={close} aria-label="Close">✕</button>
    </header>
    <div class="bar">
      <button class="btn icon" disabled={!parent} onclick={() => go(parent)} title="Up one level">↑</button>
      <button class="btn icon" onclick={() => go("__roots__")} title="Drives">⌂</button>
      <span class="path" title={path}>{isRoots ? "Drives" : path}</span>
      <button class="btn" disabled={isRoots} onclick={mkdir}>New folder</button>
    </div>
    <ul>
      {#each dirs as d (d.path)}
        <li><button disabled={!d.readable} onclick={() => go(d.path)}><span>▸</span>{d.name}</button></li>
      {:else}
        <li class="none">No folders inside this one.</li>
      {/each}
    </ul>
    <footer>
      {#if mode === "library"}
        <input class="field" placeholder="Name in the gallery (optional)" bind:value={name} />
      {/if}
      <button class="btn" onclick={close}>Cancel</button>
      <button class="btn solid" disabled={isRoots || busy || !path} onclick={confirmPick}>
        {mode === "library" ? "Add this folder" : "Copy here"}
      </button>
    </footer>
  </div>
</div>

<style>
  .veil { position: fixed; inset: 0; z-index: 50; background: rgba(0,0,0,.6); display: grid; place-items: center; animation: f .15s both; }
  @keyframes f { from { opacity: 0; } }
  .box { background: rgba(18,18,22,.94); width: min(640px, 94vw); height: min(620px, 88vh); border-radius: var(--r-lg); display: flex; flex-direction: column; animation: pop .28s var(--ease) both; }
  @keyframes pop { from { transform: translateY(14px) scale(.98); opacity: 0; } }
  header { display: flex; justify-content: space-between; align-items: center; padding: 14px 14px 10px 20px; }
  h2 { margin: 0; font-size: 17px; font-weight: 650; letter-spacing: -0.01em; }
  .bar { display: flex; gap: 6px; align-items: center; padding: 0 14px 10px; border-bottom: 1px solid var(--line); }
  .path { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dim); padding: 0 6px; }
  ul { flex: 1; overflow-y: auto; margin: 0; padding: 8px; list-style: none; }
  li button { display: flex; gap: 10px; width: 100%; padding: 7px 12px; border-radius: 8px; text-align: left; }
  li button span { color: var(--faint); }
  li button:hover { background: var(--raise); }
  li button:disabled { color: var(--faint); pointer-events: none; }
  .none { padding: 14px; color: var(--faint); }
  footer { display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--line); justify-content: flex-end; }
  footer .field { flex: 1; }
</style>
