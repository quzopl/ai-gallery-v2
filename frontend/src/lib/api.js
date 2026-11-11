export async function api(url, opts = {}) {
  const r = await fetch(url, {
    headers: opts.body ? { "content-type": "application/json" } : undefined,
    ...opts,
  });
  if (!r.ok) {
    let msg = `${r.status}`;
    try { msg = (await r.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return r.json();
}
export const post = (url, body) => api(url, { method: "POST", body: JSON.stringify(body ?? {}) });
export const del = (url) => api(url, { method: "DELETE" });
export const thumbUrl = (it) => `/api/images/${it.id}/thumb?v=${it.sha1 || ""}`;
export const fileUrl = (it) => `/api/images/${it.id}/file?v=${it.mtime || ""}`;
