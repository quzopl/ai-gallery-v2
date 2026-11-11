// A stable hue per name: colour is data here — each model family keeps its own.
export function hue(name) {
  let h = 2166136261;
  for (const c of String(name)) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return ((h >>> 0) % 360);
}
export const familyColor = (name) => name ? `oklch(0.8 0.13 ${hue(name)})` : "var(--faint)";

export function familyLabel(key) {
  const fixed = { flux1: "FLUX.1", flux2: "FLUX.2", sdxl: "SDXL", "sd1.5": "SD 1.5", zimage: "Z-Image", ltx: "LTX Video", minimax: "MiniMax", hidream: "HiDream", seedvr: "SeedVR" };
  if (!key) return "Unknown model";
  if (fixed[key]) return fixed[key];
  const m = /^([a-z]+)([\d.]*)$/.exec(key);
  return m ? `${m[1][0].toUpperCase()}${m[1].slice(1)} ${m[2]}`.trim() : key;
}
export function shortModel(name) {
  if (!name) return "";
  return name.replace(/\\/g, "/").split("/").pop().replace(/\.(safetensors|gguf|ckpt|pt|pth|sft|bin)$/i, "");
}
export function fmtDuration(s) {
  if (s == null) return "";
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}
export function fmtBytes(n) {
  if (n == null) return "";
  const u = ["B", "KB", "MB", "GB"]; let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${u[i]}`;
}
export const fmtDate = (ts) => ts ? new Date(ts * 1000).toLocaleString() : "";
export const fmtCount = (n) => (n ?? 0).toLocaleString("en-US").replace(/,/g, " ");
export const sourceLabel = (s) => ({
  comfyui: "ComfyUI", ai_gallery: "ComfyUI + plugin", a1111: "A1111 / Forge", unknown: "Unknown tool",
  invokeai: "InvokeAI", swarmui: "SwarmUI", fooocus: "Fooocus", novelai: "NovelAI",
}[s] || s || "No metadata");
