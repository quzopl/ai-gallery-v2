"""Generic model / LoRA detection — no list of known loader nodes.

Three layers:
  1. file scan   – every string anywhere in a metadata structure that looks
                   like a model file (.safetensors, .gguf, …) is classified by
                   the key / node class / path it sits under
  2. foreign     – metadata written by tools we have never seen: JSON walked
                   by key names, plain text by patterns
  3. families    – "flux2", "ideogram4", "krea2"… derived from the file name;
                   unknown names are learned and reused (FamilyRegistry)
"""
from __future__ import annotations

import json
import re
import threading
from typing import Any, Callable, Iterator

MODEL_EXT_RE = re.compile(r"\.(safetensors|gguf|ckpt|pt|pth|sft|bin|onnx)$", re.IGNORECASE)

ROLE_MODEL, ROLE_LORA, ROLE_OTHER = "model", "lora", "other"

_ENCODER_NAME_RE = re.compile(
    r"t5xxl|t5[-_]|umt5|byt5|clip[-_]?[lg]\b|clip_[lg]|llava|gemma|mistral|"
    r"qwen[-_.\d]*vl|text[-_]?enc", re.IGNORECASE)
_AUX_HINTS = ("florence", "sam_", "sam2", "yolo", "bbox", "segm", "detector", "face",
              "ipadapter", "ip-adapter", "ip_adapter", "style_model", "depth", "rife",
              "film", "insight", "reactor", "pulid", "redux", "siglip", "audio",
              "vocoder", "wav2vec", "melband", "interpol", "caption", "tagger",
              "embedding", "llm", "whisper", "sapiens", "dwpose", "openpose", "birefnet", "rembg")
_MODEL_KEYS = {"ckpt_name", "unet_name", "model_name", "model", "gguf_name",
               "diffusion_model", "checkpoint", "base_model", "transformer",
               "model_path", "ckpt", "unet", "base_ckpt_name"}
_MODEL_CLASS_HINTS = ("checkpoint", "unet", "diffusionmodel", "diffusion_model",
                      "modelloader", "loadergguf", "transformer", "loadmodel")
_STRENGTH_KEYS = ("strength", "strength_model", "weight", "lora_weight", "lora_strength",
                  "model_weight", "model_strength", "lora_wt", "strength_01")


def classify(key: str | None, class_type: str | None, value: str) -> str:
    """Role of a model file given where it was found."""
    k = (key or "").lower()
    c = (class_type or "").lower().replace(" ", "")
    v = value.lower().replace("\\", "/")
    name = v.rsplit("/", 1)[-1]
    kc = f"{k} {c}"
    if "lora" in kc or "/loras/" in f"/{v}" or v.startswith("lora"):
        return ROLE_LORA
    if "controlnet" in kc or "control_net" in kc or "controlnet" in v:
        return "controlnet"
    if "upscale" in kc or "esrgan" in name or "upscale" in v:
        return "upscaler"
    if "clip_vision" in kc or "clipvision" in kc:
        return "clip_vision"
    if "vae" in kc or "vae" in name or name.startswith("ae."):
        return "vae"
    if (k.startswith("clip") or "cliploader" in c or "textencoder" in c
            or "text_encoder" in kc or "t5" in k or _ENCODER_NAME_RE.search(name)):
        return "text_encoder"
    if any(h in kc or h in v for h in _AUX_HINTS):
        return "aux"
    if k in _MODEL_KEYS or any(h in c for h in _MODEL_CLASS_HINTS):
        return ROLE_MODEL
    return ROLE_OTHER


def _is_off(d: dict) -> bool:
    for flag in ("on", "enabled", "enable", "active"):
        if d.get(flag) is False:
            return True
    return False


def _sibling_strength(container: Any, key: Any) -> float | None:
    if isinstance(container, dict):
        if isinstance(key, str):
            m = re.search(r"(\d+)$", key)
            if m:
                for k, v in container.items():
                    if (isinstance(k, str) and k.endswith(m.group(1)) and k != key
                            and ("strength" in k.lower() or "weight" in k.lower())
                            and isinstance(v, (int, float)) and not isinstance(v, bool)):
                        return float(v)
        for k in _STRENGTH_KEYS:
            v = container.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    elif isinstance(container, list) and isinstance(key, int):
        for v in container[key + 1:key + 3]:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    return None


def iter_files(obj: Any, *, class_type: str | None = None, key: Any = None,
               _depth: int = 0) -> Iterator[tuple[str, str, float | None]]:
    """Yield (role, file, strength) for every model file inside `obj`."""
    if _depth > 12:
        return
    if isinstance(obj, dict):
        if _is_off(obj):
            return
        ct = obj.get("class_type") or obj.get("type") if isinstance(
            obj.get("class_type") or obj.get("type"), str) else class_type
        ct = ct or class_type
        for k, v in obj.items():
            if isinstance(v, str):
                if MODEL_EXT_RE.search(v.strip()):
                    yield classify(k, ct, v.strip()), v.strip(), _sibling_strength(obj, k)
            elif isinstance(v, (dict, list)):
                yield from iter_files(v, class_type=ct, key=k, _depth=_depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                if MODEL_EXT_RE.search(v.strip()):
                    yield (classify(key if isinstance(key, str) else None, class_type, v.strip()),
                           v.strip(), _sibling_strength(obj, i))
            elif isinstance(v, (dict, list)):
                yield from iter_files(v, class_type=class_type, key=key, _depth=_depth + 1)


# ---------- ComfyUI graphs ----------

_MODEL_LINK_KEYS = ("model", "guider", "unet", "diffusion_model", "transformer",
                    "pipe", "basic_pipe", "base_model", "model_high", "model_low")


def _node_model_file(node: dict) -> str | None:
    best = None
    for role, f, _ in iter_files(node.get("inputs") or {}, class_type=node.get("class_type")):
        if role == ROLE_MODEL:
            return f
        if role == ROLE_OTHER and best is None:
            best = f
    return best


def graph_model(graph: dict[str, Any]) -> str | None:
    """Main model of an API-format graph: the loader feeding the sampler,
    whatever its class is called. Falls back to the first model file."""
    nodes = {str(k): v for k, v in graph.items() if isinstance(v, dict)}
    start = [nid for nid, n in nodes.items()
             if "sampler" in str(n.get("class_type", "")).lower()]
    seen: set[str] = set()
    queue = list(start)
    while queue:
        nid = queue.pop(0)
        if nid in seen or nid not in nodes:
            continue
        seen.add(nid)
        node = nodes[nid]
        f = _node_model_file(node)
        if f:
            return f
        inp = node.get("inputs") or {}
        links = [(k, v) for k, v in inp.items()
                 if isinstance(v, list) and len(v) == 2 and isinstance(v[0], (str, int))]
        pri = [str(v[0]) for k, v in links
               if k.lower() in _MODEL_LINK_KEYS or "model" in k.lower() or "guider" in k.lower()]
        queue.extend(pri)
    # no sampler chain → first explicit model file, then first unclassified one
    other = None
    for node in nodes.values():
        for role, f, _ in iter_files(node.get("inputs") or {}, class_type=node.get("class_type")):
            if role == ROLE_MODEL:
                return f
            if role == ROLE_OTHER and other is None:
                other = f
    return other


def workflow_nodes(workflow: dict[str, Any]) -> list[dict]:
    """Active nodes of a UI-format workflow (muted=2 / bypassed=4 skipped)."""
    out = []
    for n in workflow.get("nodes") or []:
        if isinstance(n, dict) and n.get("mode") not in (2, 4):
            out.append(n)
    return out


def scan_structure(obj: Any) -> dict[str, Any]:
    """Model, LoRAs and auxiliary files of any structure (API graph, UI
    workflow, foreign JSON)."""
    model = None
    other = None
    loras: list[tuple[str, float | None]] = []
    aux: list[dict[str, str]] = []
    seen: set[str] = set()
    items = obj
    if isinstance(obj, dict) and isinstance(obj.get("nodes"), list):
        items = [{"type": n.get("type"), "w": n.get("widgets_values")} for n in workflow_nodes(obj)]
    for role, f, strength in iter_files(items):
        if f in seen:
            continue
        seen.add(f)
        if role == ROLE_LORA:
            loras.append((f, strength))
        elif role == ROLE_MODEL:
            model = model or f
        elif role == ROLE_OTHER:
            other = other or f
        else:
            aux.append({"role": role, "name": f})
    return {"model": model or other, "loras": loras, "aux": aux}


# ---------- foreign / unknown metadata ----------

_PROMPT_KEYS = ("prompt", "positive_prompt", "positive", "full_prompt", "description",
                "caption", "text", "input_prompt", "user_prompt")
_NEG_KEYS = ("negative_prompt", "negative", "uc", "neg_prompt", "negativeprompt")
_MODEL_NAME_KEYS = ("model", "model_name", "sd_model_name", "base_model", "base_model_name",
                    "checkpoint", "ckpt", "sd_model", "model_id", "modelname", "base model")
_SCALAR_MAP = {
    "seed": ("seed", "noise_seed"),
    "steps": ("steps", "num_inference_steps", "sampling_steps"),
    "cfg": ("cfg", "cfg_scale", "guidance_scale", "guidance", "scale", "cfgscale"),
    "sampler": ("sampler", "sampler_name", "scheduler", "sampling_method"),
}
_SOURCE_HINTS = (
    ("invokeai", "invokeai"), ("sui_image_params", "swarmui"), ("swarm", "swarmui"),
    ("fooocus", "fooocus"), ("novelai", "novelai"), ("draw things", "drawthings"),
    ("drawthings", "drawthings"), ("midjourney", "midjourney"), ("easy diffusion", "easydiffusion"),
    ("forge", "forge"), ("stable diffusion", "stable-diffusion"), ("dall", "dalle"),
    ("firefly", "firefly"), ("leonardo", "leonardo"), ("civitai", "civitai"),
    ("mochi diffusion", "mochidiffusion"), ("krita", "krita"), ("comfy", "comfyui"),
)
_TEXT_MODEL_RE = re.compile(
    r"(?im)(?:^|[,;\n])\s*(?:model|checkpoint|base model|sd model)\s*[:=]\s*\"?([^,\n\"]+)")
_TEXT_LORA_RE = re.compile(r"<lora:([^:>]+)(?::([-\d.]+))?[^>]*>", re.IGNORECASE)


def _loads(s: Any) -> Any:
    if not isinstance(s, str):
        return None
    t = s.strip()
    if not t or t[0] not in "{[":
        return None
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None


def _name_of(v: Any) -> str | None:
    if isinstance(v, str):
        v = v.strip()
        return v if v and v.lower() not in ("none", "null", "unknown") and len(v) < 200 else None
    if isinstance(v, dict):
        for k in ("name", "model_name", "title", "key", "id"):
            n = _name_of(v.get(k)) if not isinstance(v.get(k), dict) else None
            if n:
                return n
    return None


def _walk_named(obj: Any, found: dict[str, Any], depth: int = 0) -> None:
    if depth > 10:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower().replace(" ", "_") if isinstance(k, str) else ""
            if isinstance(v, str):
                inner = _loads(v)
                if inner is not None:
                    _walk_named(inner, found, depth + 1)
                    continue
            if kl in _PROMPT_KEYS and isinstance(v, str) and v.strip():
                found.setdefault("prompt", v.strip())
            elif kl in _NEG_KEYS and isinstance(v, str) and v.strip():
                found.setdefault("negative", v.strip())
            elif kl in _MODEL_NAME_KEYS and _name_of(v):
                found.setdefault("model_name", _name_of(v))
            elif kl in ("loras", "lora") and isinstance(v, list):
                for item in v:
                    n = None
                    w = None
                    if isinstance(item, dict):
                        n = _name_of(item.get("model")) or _name_of(item.get("lora")) or _name_of(item)
                        for wk in ("weight", "strength", "model_strength", "scale"):
                            if isinstance(item.get(wk), (int, float)):
                                w = float(item[wk])
                                break
                    elif isinstance(item, str):
                        n = _name_of(item)
                    if n:
                        found.setdefault("loras", []).append((n, w))
            else:
                for field, keys in _SCALAR_MAP.items():
                    if kl in keys and isinstance(v, (int, float, str)) and not isinstance(v, bool):
                        found.setdefault(field, v)
            if isinstance(v, (dict, list)):
                _walk_named(v, found, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                _walk_named(v, found, depth + 1)


def guess_source(chunks: dict[str, str]) -> str:
    hay = " ".join(list(chunks.keys()) + [chunks.get(k, "")[:200] for k in
                                           ("Software", "software", "Source", "generator", "Generator")]).lower()
    for needle, name in _SOURCE_HINTS:
        if re.search(rf"(?<![a-z0-9]){re.escape(needle)}", hay):
            return name
    sw = chunks.get("Software") or chunks.get("software")
    if sw and len(sw) < 40:
        return re.sub(r"[^a-z0-9]+", "-", sw.lower()).strip("-") or "unknown"
    return "unknown"


def parse_foreign(chunks: dict[str, str]) -> dict[str, Any] | None:
    """Best-effort read of metadata from an unknown writer.
    Returns None when nothing generation-related was found."""
    found: dict[str, Any] = {}
    files_model = None
    loras: list[tuple[str, float | None]] = []
    aux: list[dict[str, str]] = []
    for key, val in chunks.items():
        if not isinstance(val, str) or not val.strip():
            continue
        data = _loads(val)
        if data is not None:
            _walk_named(data, found)
            scan = scan_structure(data)
            files_model = files_model or scan["model"]
            loras += scan["loras"]
            aux += scan["aux"]
            continue
        kl = key.lower().replace(" ", "_")
        if kl in _PROMPT_KEYS and len(val) < 20000:
            found.setdefault("prompt", val.strip())
        elif kl in _NEG_KEYS:
            found.setdefault("negative", val.strip())
        elif kl in _MODEL_NAME_KEYS and _name_of(val):
            found.setdefault("model_name", _name_of(val))
        m = _TEXT_MODEL_RE.search(val)
        if m and "model_name" not in found:
            found["model_name"] = m.group(1).strip()
        for name, w in _TEXT_LORA_RE.findall(val):
            try:
                loras.append((name, float(w) if w else None))
            except ValueError:
                loras.append((name, None))
    if files_model:
        found["model_name"] = files_model          # a real file name beats a label
    for n, w in found.pop("loras", []):
        loras.append((n, w))
    dedup: dict[str, float | None] = {}
    for n, w in loras:
        dedup.setdefault(n, w)
    if not found and not dedup:
        return None
    out: dict[str, Any] = {"loras": list(dedup.items()), "aux": aux}
    out.update(found)
    for k, cast in (("seed", int), ("steps", int), ("cfg", float)):
        if k in out:
            try:
                out[k] = cast(float(out[k]))
            except (TypeError, ValueError):
                out.pop(k)
    if "sampler" in out and not isinstance(out["sampler"], str):
        out.pop("sampler")
    return out


# ---------- model families ----------

SEED_BASES = (
    "flux", "ideogram", "krea", "zimage", "chroma", "wan", "ltx", "hunyuan", "qwen",
    "hidream", "sdxl", "sd3", "sd15", "pony", "illustrious", "noobai", "cosmos", "lumina",
    "auraflow", "kolors", "pixart", "sana", "mochi", "cogvideo", "minimax", "omnigen",
    "kandinsky", "playground", "cascade", "seedream", "kontext", "animatediff", "svd",
)
_ALIASES = {"flux": "flux1", "kontext": "flux1", "sd15": "sd1.5", "pony": "sdxl",
            "illustrious": "sdxl", "noobai": "sdxl"}
_LABELS = {"flux1": "FLUX.1", "flux2": "FLUX.2", "sdxl": "SDXL", "sd1.5": "SD 1.5",
           "zimage": "Z-Image", "ltx": "LTX Video", "svd": "SVD", "hidream": "HiDream",
           "cogvideo": "CogVideo", "pixart": "PixArt", "auraflow": "AuraFlow",
           "animatediff": "AnimateDiff", "minimax": "MiniMax", "noobai": "NoobAI"}
_NOISE = {
    "model", "models", "diffusion", "unet", "checkpoint", "checkpoints", "ckpt", "dev",
    "the", "new", "final", "base", "turbo", "fast", "lite", "full", "pruned", "ema", "fp8",
    "fp16", "fp32", "bf16", "scaled", "gguf", "safetensors", "int8", "mixed", "real",
    "merge", "merged", "mix", "ultra", "pro", "version", "raw", "distilled", "transformer",
    "video", "image", "comfy", "comfyui", "official", "original", "unknown", "none",
}


def _norm(name: str) -> str:
    stem = name.replace("\\", "/").rsplit("/", 1)[-1]
    stem = MODEL_EXT_RE.sub("", stem)
    return re.sub(r"[^a-z0-9]", "", stem.lower())


def _tokens(name: str) -> list[str]:
    stem = MODEL_EXT_RE.sub("", name.replace("\\", "/").rsplit("/", 1)[-1])
    stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    return [t.lower() for t in re.findall(r"[A-Za-z]+", stem)]


def family_label(key: str) -> str:
    if key in _LABELS:
        return _LABELS[key]
    m = re.fullmatch(r"([a-z]+)([\d.]*)", key)
    if not m:
        return key
    base, ver = m.groups()
    return f"{base.capitalize()} {ver}".strip()


class FamilyRegistry:
    """Known model-name stems. Unknown models teach it new ones."""

    def __init__(self, learned: tuple[str, ...] | list[str] = (),
                 on_learn: Callable[[str], None] | None = None) -> None:
        self._lock = threading.Lock()
        self.learned: list[str] = [b for b in learned if b not in SEED_BASES]
        self.on_learn = on_learn

    def bases(self) -> list[str]:
        return list(SEED_BASES) + self.learned

    def _match(self, norm: str) -> tuple[int, str] | None:
        best: tuple[int, int, str] | None = None
        for b in self.bases():
            pos = norm.find(b)
            if pos < 0:
                continue
            cand = (pos, -len(b), b)
            if best is None or cand < best:
                best = cand
        if best is None and (norm.startswith("v15") or "sd15" in norm):
            return 0, "sd15"
        if best is None and "xl" in norm:
            return norm.find("xl"), "sdxl"
        return (best[0], best[2]) if best else None

    def family(self, model_name: str | None) -> str | None:
        if not model_name or not isinstance(model_name, str):
            return None
        norm = _norm(model_name)
        if not norm:
            return None
        hit = self._match(norm)
        if hit is None:
            base = self._learn(model_name)
            if base is None:
                return None
            hit = (norm.find(base), base)
            if hit[0] < 0:
                return base
        pos, base = hit
        digits = re.match(r"\d*", norm[pos + len(base):]).group(0)
        ver = ""
        if base not in ("sdxl", "sd3", "sd15"):
            if len(digits) == 1 and digits != "0":
                ver = digits
            elif len(digits) == 2 and digits[0] != "0":
                ver = digits[0] if digits[1] == "0" else f"{digits[0]}.{digits[1]}"
        key = base + ver
        return _ALIASES.get(key, _ALIASES.get(base, key) if not ver else key)

    def _learn(self, model_name: str) -> str | None:
        for tok in _tokens(model_name):
            if len(tok) >= 4 and tok not in _NOISE:
                with self._lock:
                    if tok not in self.learned:
                        self.learned.append(tok)
                        new = True
                    else:
                        new = False
                if new and self.on_learn:
                    try:
                        self.on_learn(tok)
                    except Exception:  # noqa: BLE001
                        pass
                return tok
        return None


REGISTRY = FamilyRegistry()
