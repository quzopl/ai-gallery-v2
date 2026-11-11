"""Generate a demo library: abstract procedural images and short videos with
realistic embedded metadata (ComfyUI graphs, A1111 parameters, an unknown
tool). Nothing here is a real photo or a real generation.

    python tools/make_demo.py /path/to/demo-library
"""
from __future__ import annotations

import colorsys
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from PIL.PngImagePlugin import PngInfo

SIZES = [(832, 1216), (1216, 832), (1024, 1024), (896, 1152), (1344, 768), (768, 1344)]

SUBJECTS = {
    "nebulae": ["a drifting nebula of {a} and {b} gas, soft volumetric light, deep space",
                "luminous interstellar clouds in {a} and {b}, long exposure, fine grain"],
    "liquid": ["macro shot of {a} ink blooming in {b} water, slow motion, studio light",
               "swirling {a} and {b} pigments in oil, abstract fluid art, high detail"],
    "glass": ["frosted glass spheres lit in {a} and {b}, shallow depth of field, minimal",
              "stacked translucent {a} discs on a {b} backdrop, soft shadows, product photo"],
    "dunes": ["minimal {a} dunes under a {b} sky, wide angle, calm, editorial landscape",
              "abstract rolling hills in {a} fading to {b}, morning haze, 35mm"],
}
COLORS = ["teal", "amber", "magenta", "indigo", "coral", "lime", "violet", "cyan", "crimson", "gold"]
NEG = "blurry, low quality, watermark, text, jpeg artifacts"

# (model file, loader class, key, [LoRAs])
MODELS = [
    ("flux1-dev-fp8.safetensors", "UNETLoader", "unet_name",
     ["styles/soft_grain_v2.safetensors", "light/volumetric_haze.safetensors"]),
    ("flux2_dev_fp8mixed.safetensors", "UNETLoader", "unet_name",
     ["styles/soft_grain_v2.safetensors", "color/duotone_wash.safetensors"]),
    ("flux2-dev-Q8_0.gguf", "UnetLoaderGGUF", "unet_name", ["color/duotone_wash.safetensors"]),
    ("krea2_turbo_bf16.safetensors", "UNETLoader", "unet_name", ["macro/liquid_bloom.safetensors"]),
    ("z_image_turbo_bf16.safetensors", "UNETLoader", "unet_name", []),
    ("juggernautXL_v9.safetensors", "CheckpointLoaderSimple", "ckpt_name",
     ["sdxl/film_emulation.safetensors"]),
    ("nebula3_base_fp8.safetensors", "BrandNewModelLoader", "weights", ["light/volumetric_haze.safetensors"]),
]
SAMPLERS = ["euler", "dpmpp_2m", "res_multistep", "ipndm"]


def art(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """Soft abstract composition: blurred colour blobs on a dark gradient."""
    w, h = size
    hue = rng.random()
    def col(dh: float, s: float, v: float) -> tuple[int, int, int]:
        r, g, b = colorsys.hsv_to_rgb((hue + dh) % 1, s, v)
        return int(r * 255), int(g * 255), int(b * 255)
    top, bottom = col(0, 0.7, 0.18), col(0.08, 0.8, 0.05)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)))
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for _ in range(rng.randint(5, 9)):
        r = rng.randint(min(w, h) // 8, min(w, h) // 2)
        x, y = rng.randint(-r // 2, w), rng.randint(-r // 2, h)
        ld.ellipse([x, y, x + r, y + r], fill=col(rng.choice([0, 0.05, 0.45, 0.55]), rng.uniform(0.5, 0.95), rng.uniform(0.6, 1)))
    layer = layer.filter(ImageFilter.GaussianBlur(min(w, h) // 14))
    img = Image.blend(img, layer, 0.78)
    sharp = ImageDraw.Draw(img)
    for _ in range(rng.randint(2, 4)):
        r = rng.randint(min(w, h) // 14, min(w, h) // 5)
        x, y = rng.randint(0, w - r), rng.randint(0, h - r)
        sharp.ellipse([x, y, x + r, y + r], outline=col(0.5, 0.25, 1), width=max(2, r // 40))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def graph(model: tuple, prompt: str, rng: random.Random, *, caption_json: bool = False) -> dict:
    name, loader, key, loras = model
    g: dict = {"1": {"class_type": loader, "inputs": {key: name}}}
    last = "1"
    use = rng.sample(loras, k=rng.randint(0, len(loras)))
    if use:
        g["2"] = {"class_type": "Power Lora Loader (rgthree)", "inputs": {"model": ["1", 0], **{
            f"lora_{i + 1}": {"on": True, "lora": l, "strength": round(rng.uniform(0.4, 1.1), 2)}
            for i, l in enumerate(use)}}}
        last = "2"
    g["3"] = {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors"}}
    g["4"] = {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}}
    g["5"] = {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["3", 0]}}
    g["6"] = {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["3", 0]}}
    g["7"] = {"class_type": "KSampler", "inputs": {
        "model": [last, 0], "positive": ["5", 0], "negative": ["6", 0],
        "seed": rng.randint(1, 2**48), "steps": rng.choice([8, 20, 28, 40]),
        "cfg": rng.choice([1.0, 3.5, 4.5, 7.0]), "sampler_name": rng.choice(SAMPLERS), "scheduler": "simple"}}
    return g


def ideogram_caption(prompt: str, a: str, b: str) -> str:
    return json.dumps({
        "aspect_ratio": "3:4",
        "high_level_description": prompt,
        "background": {"description": f"A deep {b} backdrop fading to black at the edges."},
        "foreground": [{"description": f"Soft {a} forms drifting across the centre of the frame."}],
        "style": {"medium": "abstract digital painting", "lighting": "soft volumetric"},
    }, indent=2)


def main(root: Path) -> None:
    rng = random.Random(7)
    if root.exists():
        shutil.rmtree(root)
    now = time.time()
    n = 0

    def stamp(p: Path) -> None:
        nonlocal n
        t = now - n * 5400
        os.utime(p, (t, t))
        n += 1

    for folder, templates in SUBJECTS.items():
        (root / folder).mkdir(parents=True)
        for i in range(16):
            a, b = rng.sample(COLORS, 2)
            prompt = rng.choice(templates).format(a=a, b=b)
            info = PngInfo()
            kind = rng.random()
            if kind < 0.14:      # Ideogram-style structured caption
                g = graph(("ideogram4_fp8_scaled.safetensors", "UNETLoader", "unet_name", []), ideogram_caption(prompt, a, b), rng)
                info.add_text("prompt", json.dumps(g))
            elif kind < 0.22:    # A1111 / Forge
                info.add_text("parameters", f"{prompt} <lora:film_emulation:0.7>\nNegative prompt: {NEG}\n"
                              f"Steps: 30, Sampler: DPM++ 2M, CFG scale: 6.5, Seed: {rng.randint(1, 2**31)}, "
                              f"Size: 832x1216, Model: juggernautXL_v9, Version: f2.0")
            elif kind < 0.30:    # a tool the gallery has never seen
                info.add_text("Software", "PixelForge 3")
                info.add_text("pf_meta", json.dumps({"prompt": prompt, "negative_prompt": NEG,
                              "model": "aurora3_base.safetensors", "seed": rng.randint(1, 2**31), "steps": 24,
                              "cfg_scale": 5.0, "loras": [{"name": "glow_trails", "weight": 0.6}]}))
            else:
                info.add_text("prompt", json.dumps(graph(rng.choice(MODELS), prompt, rng)))
            p = root / folder / f"{folder}_{i + 1:05d}_.png"
            art(rng.choice(SIZES), rng).save(p, pnginfo=info)
            stamp(p)

    # a folder of throwaway test renders — good for trying "hide this folder"
    (root / "tests").mkdir()
    for i in range(6):
        p = root / "tests" / f"test_{i + 1:03d}.png"
        art((768, 768), rng).save(p)
        stamp(p)

    if shutil.which("ffmpeg"):
        (root / "video").mkdir()
        clips = [
            ("gradients=s=832x480:d=4:speed=0.02:r=24", "wan2.2_t2v_high_noise_14B_fp8.safetensors", "slow flowing colour fields, seamless loop"),
            ("mandelbrot=s=640x640:r=24", "wan2.2_t2v_high_noise_14B_fp8.safetensors", "endless fractal zoom, cinematic"),
            ("gradients=s=480x832:d=5:speed=0.05:r=24:c0=0x1b0a3a:c1=0xff3d81", "ltx-video-2b-v0.9.5.safetensors", "magenta light leaking through fog, vertical"),
            ("life=s=640x360:mold=10:r=24:ratio=0.1:death_color=0x102040:life_color=0x70e0ff", "ltx-video-2b-v0.9.5.safetensors", "bioluminescent cells spreading, top view"),
        ]
        for i, (src, model, prompt) in enumerate(clips):
            g = graph((model, "UNETLoader", "unet_name", []), prompt, rng)
            p = root / "video" / f"clip_{i + 1:05d}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-t", "4",
                            "-pix_fmt", "yuv420p", "-movflags", "use_metadata_tags",
                            "-metadata", f"prompt={json.dumps(g)}", str(p)], check=True)
            n_before = n
            stamp(p)
            # sprinkle the clips among the newest files
            t = now - (i * 9 + 2) * 5400
            os.utime(p, (t, t))
            n = n_before
    print(f"demo library written to {root}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "demo-library").resolve())
