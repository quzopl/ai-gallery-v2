<script>
  import { S, loadMore } from "./store.svelte.js";
  import { thumbUrl, fileUrl } from "./api.js";
  import { familyColor, familyLabel, fmtDuration } from "./util.js";

  let { onopen } = $props();
  const GAP = 6;
  let el = $state(null);
  let width = $state(0), viewH = $state(0), top = $state(0);
  let hoverId = $state(null);
  let hoverTimer;

  const layout = $derived.by(() => {
    const n = S.items.length;
    const w = Math.max(0, width);
    const cols = Math.max(1, Math.floor((w + GAP) / (S.tile + GAP)));
    const cw = (w - GAP * (cols - 1)) / cols;
    const rects = new Array(n);
    let height = 0;
    if (S.view === "grid") {
      for (let i = 0; i < n; i++) {
        rects[i] = { x: (i % cols) * (cw + GAP), y: Math.floor(i / cols) * (cw + GAP), w: cw, h: cw };
      }
      height = Math.ceil(n / cols) * (cw + GAP);
    } else {
      const hs = new Array(cols).fill(0);
      for (let i = 0; i < n; i++) {
        const it = S.items[i];
        const ar = it.width && it.height ? Math.min(2.2, Math.max(0.45, it.height / it.width)) : 1;
        let c = 0;
        for (let k = 1; k < cols; k++) if (hs[k] < hs[c] - 0.5) c = k;
        rects[i] = { x: c * (cw + GAP), y: hs[c], w: cw, h: cw * ar };
        hs[c] += cw * ar + GAP;
      }
      height = Math.max(0, ...hs);
    }
    return { rects, height, cols };
  });

  const visible = $derived.by(() => {
    const out = [], a = top - 900, b = top + viewH + 900, r = layout.rects;
    for (let i = 0; i < r.length; i++) if (r[i].y + r[i].h > a && r[i].y < b) out.push(i);
    return out;
  });

  $effect(() => {
    if (layout.height - (top + viewH) < 1800) loadMore();
  });

  $effect(() => {
    if (!el) return;
    const ro = new ResizeObserver(() => { width = el.clientWidth - 32; viewH = el.clientHeight; });
    ro.observe(el);
    return () => ro.disconnect();
  });

  let raf = 0;
  function onscroll() {
    if (raf) return;
    raf = requestAnimationFrame(() => { raf = 0; top = el.scrollTop; });
  }

  export function cols() { return layout.cols; }
  export function reveal(id) {
    const i = S.items.findIndex((x) => x.id === id);
    const r = layout.rects[i];
    if (!r || !el) return;
    if (r.y < el.scrollTop + 8) el.scrollTo({ top: Math.max(0, r.y - 12) });
    else if (r.y + r.h > el.scrollTop + viewH - 8) el.scrollTo({ top: r.y + r.h - viewH + 28 });
  }
  export function toTop() { el?.scrollTo({ top: 0 }); }

  function enter(it) {
    clearTimeout(hoverTimer);
    if (it.media_kind === "video") hoverTimer = setTimeout(() => (hoverId = it.id), 220);
  }
  function leave() { clearTimeout(hoverTimer); hoverId = null; }
</script>

<div class="scroll" bind:this={el} {onscroll}>
  <div class="canvas" style:height="{layout.height}px">
    {#each visible as i (S.items[i].id)}
      {@const it = S.items[i]}
      {@const r = layout.rects[i]}
      <button
        class="tile" class:focus={S.focusId === it.id}
        data-id={it.id}
        style:transform="translate({r.x}px,{r.y}px)" style:width="{r.w}px" style:height="{r.h}px"
        style:--fam={familyColor(it.family)}
        onclick={(e) => onopen(it.id, e.currentTarget)}
        onmouseenter={() => enter(it)} onmouseleave={leave}
        aria-label={it.rel_path}
      >
        <img src={thumbUrl(it)} alt="" loading="lazy" decoding="async" draggable="false" />
        {#if hoverId === it.id}
          <video src={fileUrl(it)} muted loop autoplay playsinline></video>
        {/if}
        {#if it.media_kind === "video"}
          <span class="badge">▶ {fmtDuration(it.duration)}</span>
        {/if}
        {#if it.is_favorite}<span class="star">★</span>{/if}
        <span class="strip">
          <i></i>{familyLabel(it.family)}
        </span>
      </button>
    {/each}
  </div>
  {#if !S.items.length && !S.loading}
    <div class="empty">
      {#if !S.libraries.length}
        <h2>No folders yet</h2>
        <p>Add a folder with your generated images and videos. The gallery reads prompts, models and LoRAs straight from the files.</p>
      {:else}
        <h2>Nothing matches these filters</h2>
        <p>Remove a filter or clear the search to see more.</p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .scroll { height: 100%; overflow-y: auto; padding: 0 16px 40px; }
  .canvas { position: relative; }
  .tile {
    position: absolute; left: 0; top: 0; overflow: hidden; border-radius: 6px;
    background: #101014; contain: strict;
    animation: in .35s var(--ease) both;
  }
  @keyframes in { from { opacity: 0; } }
  .tile img, .tile video {
    position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
    transition: transform .5s var(--ease), filter .3s;
  }
  .tile:hover img, .tile:hover video { transform: scale(1.045); }
  .tile.focus { outline: 2px solid #fff; outline-offset: -2px; z-index: 1; }
  .strip {
    position: absolute; left: 0; right: 0; bottom: 0; padding: 22px 9px 7px;
    display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 550; text-align: left;
    background: linear-gradient(transparent, rgba(0,0,0,.78));
    opacity: 0; transform: translateY(6px); transition: opacity .2s, transform .25s var(--ease);
    white-space: nowrap; overflow: hidden;
  }
  .strip i { width: 8px; height: 8px; border-radius: 50%; background: var(--fam); flex: none; box-shadow: 0 0 10px var(--fam); }
  .tile:hover .strip, .tile.focus .strip { opacity: 1; transform: none; }
  .badge {
    position: absolute; top: 7px; left: 7px; padding: 2px 7px; border-radius: 20px; font-size: 11px; font-weight: 600;
    background: rgba(0,0,0,.6); backdrop-filter: blur(8px);
  }
  .star { position: absolute; top: 5px; right: 8px; color: var(--gold); font-size: 15px; text-shadow: 0 1px 6px #000; }
  .empty { max-width: 46ch; margin: 18vh auto 0; text-align: center; color: var(--dim); }
  .empty h2 { color: var(--text); font-size: 22px; font-weight: 600; margin: 0 0 8px; letter-spacing: -0.01em; }
  .empty p { margin: 0; }
</style>
