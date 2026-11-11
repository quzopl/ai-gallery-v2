from __future__ import annotations
import json
import pytest
from backend import detect
from backend.detect import FamilyRegistry


@pytest.mark.parametrize("name,fam", [
    ("flux1DevFp8_v10.safetensors", "flux1"),
    ("flux1-dev-fp8.safetensors", "flux1"),
    ("flux_dev.safetensors", "flux1"),
    ("flux2_dev_fp8mixed.safetensors", "flux2"),
    ("flux-2-klein-base-9b.safetensors", "flux2"),
    ("flux2-dev-int8-convrot-aggressive.safetensors", "flux2"),
    ("ideogram4_unconditional_fp8_scaled.safetensors", "ideogram4"),
    ("krea2_turbo_bf16.safetensors", "krea2"),
    ("krea2TurboFP8_krea2TURBO.safetensors", "krea2"),
    ("Krea2-Turbo-int8-ConvRot.safetensors", "krea2"),
    ("z_image_turbo_bf16.safetensors", "zimage"),
    ("chroma-unlocked-v32_float8_e4m3fn_scaled_stochastic.safetensors", "chroma"),
    ("midjourneyReplica_flux1Dev.safetensors", "flux1"),
    ("realflux10b_10bTransformerDev.safetensors", "flux1"),
    ("fluxmania_V.safetensors", "flux1"),
    ("unet/wan2.2_t2v_high_noise_14B_fp8.safetensors", "wan2.2"),
    ("Wan2_1-T2V-14B_fp8.safetensors", "wan2.1"),
    ("juggernautXL_v9.safetensors", "sdxl"),
    ("sd3.5_large.safetensors", "sd3"),
    ("v1-5-pruned-emaonly.ckpt", "sd1.5"),
    (None, None),
])
def test_family_seeded(name, fam) -> None:
    assert FamilyRegistry().family(name) == fam


def test_family_learns_unknown_and_reuses() -> None:
    learned: list[str] = []
    reg = FamilyRegistry(on_learn=learned.append)
    assert reg.family("Nebula3_dev_fp8.safetensors") == "nebula3"
    assert learned == ["nebula"]
    # learned stem is now an expression matched anywhere in later names
    assert reg.family("custom_merge_nebula3_turbo.gguf") == "nebula3"
    assert reg.family("nebula-4-base.safetensors") == "nebula4"
    assert learned == ["nebula"]
    assert FamilyRegistry(learned=["nebula"]).family("xx_nebula2.safetensors") == "nebula2"


def test_family_label() -> None:
    assert detect.family_label("flux2") == "FLUX.2"
    assert detect.family_label("ideogram4") == "Ideogram 4"
    assert detect.family_label("wan2.2") == "Wan 2.2"
    assert detect.family_label("zimage") == "Z-Image"


def test_graph_model_unknown_loader_traced_from_sampler() -> None:
    g = {
        "1": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x_foo.safetensors"}},
        "2": {"class_type": "SomeBrandNewLoaderXYZ", "inputs": {"file": "refiner_other.safetensors"}},
        "3": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}},
        "4": {"class_type": "ModelSamplingFlux", "inputs": {"model": ["3", 0]}},
        "5": {"class_type": "DualCLIPLoaderGGUF", "inputs": {"clip_name1": "t5xxl_fp8.safetensors", "clip_name2": "clip_l.safetensors"}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "seed": 1}},
    }
    assert detect.graph_model(g) == "flux1-dev-Q8_0.gguf"
    s = detect.scan_structure(g)
    roles = {a["name"]: a["role"] for a in s["aux"]}
    assert roles["ae.safetensors"] == "vae"
    assert roles["t5xxl_fp8.safetensors"] == "text_encoder"
    assert roles["4x_foo.safetensors"] == "upscaler"


def test_graph_model_alien_loader_no_sampler() -> None:
    g = {"9": {"class_type": "TotallyAlienNode", "inputs": {"weights": "mystery_v2.safetensors", "vae": "x_vae.pt"}}}
    assert detect.graph_model(g) == "mystery_v2.safetensors"


def test_scan_generic_loras_and_disabled() -> None:
    g = {
        "1": {"class_type": "AlienStack", "inputs": {
            "a": {"on": True, "lora": "styles/neon.safetensors", "strength": 0.7},
            "b": {"on": False, "lora": "off.safetensors", "strength": 1.0}}},
        "2": {"class_type": "MysteryPatcher", "inputs": {"lora_file_2": "loras/grain.safetensors", "weight_2": 0.4}},
    }
    s = detect.scan_structure(g)
    assert s["loras"] == [("styles/neon.safetensors", 0.7), ("loras/grain.safetensors", 0.4)]


def test_scan_ui_workflow_skips_bypassed() -> None:
    wf = {"nodes": [
        {"type": "UNETLoader", "mode": 0, "widgets_values": ["krea2_turbo_bf16.safetensors", "default"]},
        {"type": "LoraLoaderModelOnly", "mode": 0, "widgets_values": ["a.safetensors", 0.8]},
        {"type": "LoraLoaderModelOnly", "mode": 4, "widgets_values": ["bypassed.safetensors", 1.0]},
    ]}
    s = detect.scan_structure(wf)
    assert s["model"] == "krea2_turbo_bf16.safetensors"
    assert s["loras"] == [("a.safetensors", 0.8)]


def test_parse_foreign_json_chunk() -> None:
    chunks = {"some_plugin_meta": json.dumps({
        "generation": {"positive_prompt": "a red fox", "negative_prompt": "blurry",
                       "base_model": {"name": "NovaDream 3"}, "cfg_scale": 4.5, "steps": "30", "seed": 77,
                       "loras": [{"model": {"name": "furry"}, "weight": 0.6}]}})}
    r = detect.parse_foreign(chunks)
    assert r["prompt"] == "a red fox" and r["negative"] == "blurry"
    assert r["model_name"] == "NovaDream 3"
    assert r["cfg"] == 4.5 and r["steps"] == 30 and r["seed"] == 77
    assert r["loras"] == [("furry", 0.6)]
    assert detect.guess_source(chunks) == "unknown"


def test_parse_foreign_text_and_source() -> None:
    chunks = {"Software": "SuperGen 2", "Comment": "cat <lora:whiskers:0.5>\nModel: supergen_v2.safetensors, Seed: 5"}
    r = detect.parse_foreign(chunks)
    assert r["model_name"] == "supergen_v2.safetensors"
    assert r["loras"] == [("whiskers", 0.5)]
    assert detect.guess_source(chunks) == "supergen-2"
    assert detect.parse_foreign({"dpi": "72"}) is None
    assert detect.guess_source({"invokeai_metadata": "{}"}) == "invokeai"
