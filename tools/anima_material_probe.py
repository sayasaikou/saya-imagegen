# -*- coding: utf-8 -*-
"""Same-seed material probe: baseline vs detail LoRAs.

Runs one prompt with the same seed across a list of LoRA stacks and saves every output
next to each other. Used to answer "does this detail LoRA actually change material
rendering, or only sharpen the image?"

Usage:
    python anima_material_probe.py --host http://127.0.0.1:8188 \
        --comfy-out <ComfyUI output dir> --outdir <result dir> [--case base]
"""
import argparse
import json
import os
import shutil
import time
import urllib.request

DEFAULT_PROMPT = (
    "1girl, solo, long light blue hair, white dress with asymmetric hem, standing among "
    "blue flowers, soft afternoon sunlight, painterly illustration, detailed skin texture, "
    "subsurface scattering on skin, realistic woven fabric with fine folds, polished metal "
    "ornaments, cinematic lighting, shallow depth of field, masterpiece, best quality"
)
DEFAULT_NEG = "worst quality, low quality, blurry, jpeg artifacts, flat lighting, cel shading"

# tag -> list of (lora filename, strength)
CASES = {
    "base": [],
    "sb08": [("Smooth_Booster_Anima.safetensors", 0.8)],
    "sb08_md03": [("Smooth_Booster_Anima.safetensors", 0.8),
                  ("AddMicroDetails_Anima_v1.safetensors", 0.3)],
    "sb08_md05": [("Smooth_Booster_Anima.safetensors", 0.8),
                  ("AddMicroDetails_Anima_v1.safetensors", 0.5)],
    "sb08_md08": [("Smooth_Booster_Anima.safetensors", 0.8),
                  ("AddMicroDetails_Anima_v1.safetensors", 0.8)],
    "sb10_md03": [("Smooth_Booster_Anima.safetensors", 1.0),
                  ("AddMicroDetails_Anima_v1.safetensors", 0.3)],
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="http://127.0.0.1:8188")
    p.add_argument("--comfy-out", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--unet", default="anima-aesthetic-v1.1.safetensors")
    p.add_argument("--clip", default="qwen_3_06b_base.safetensors")
    p.add_argument("--vae", default="qwen_image_vae.safetensors")
    p.add_argument("--clip-type", default="stable_diffusion")
    p.add_argument("--prompt-file", default="")
    p.add_argument("--seed", type=int, default=20261020)
    p.add_argument("--width", type=int, default=832)
    p.add_argument("--height", type=int, default=1216)
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--cfg", type=float, default=4.0)
    p.add_argument("--case", default="")
    return p.parse_args()


def post(host, path, payload):
    req = urllib.request.Request(host + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read().decode())


def get(host, path):
    return json.loads(urllib.request.urlopen(host + path, timeout=180).read().decode())


def build(a, prompt, negative, tag, loras):
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": a.unet, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": a.clip, "type": a.clip_type}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": a.vae}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "6": {"class_type": "EmptySD3LatentImage",
              "inputs": {"width": a.width, "height": a.height, "batch_size": 1}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage",
               "inputs": {"filename_prefix": "probe_" + tag, "images": ["9", 0]}},
    }
    model = ["1", 0]
    for i, (name, strength) in enumerate(loras):
        node = "L%d" % i
        wf[node] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": model, "lora_name": name, "strength_model": strength}}
        model = [node, 0]
    wf["7"] = {"class_type": "KSampler",
               "inputs": {"seed": a.seed, "steps": a.steps, "cfg": a.cfg,
                          "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
                          "model": model, "positive": ["4", 0], "negative": ["5", 0],
                          "latent_image": ["6", 0]}}
    return wf


def main():
    args = parse_args()
    prompt = DEFAULT_PROMPT
    if args.prompt_file:
        prompt = open(args.prompt_file, encoding="utf-8").read().strip()
    os.makedirs(args.outdir, exist_ok=True)

    for tag, loras in CASES.items():
        if args.case and args.case != tag:
            continue
        started = time.time()
        try:
            response = post(args.host, "/prompt", {"prompt": build(args, prompt, DEFAULT_NEG, tag, loras)})
        except Exception as exc:  # noqa: BLE001
            body = exc.read().decode() if hasattr(exc, "read") else str(exc)
            print("SUBMIT FAIL", tag, body[:600], flush=True)
            continue
        prompt_id = response["prompt_id"]
        outputs = None
        while time.time() - started < 1800:
            time.sleep(2)
            history = get(args.host, "/history/" + prompt_id)
            if prompt_id in history:
                status = history[prompt_id].get("status", {})
                if status.get("completed"):
                    outputs = history[prompt_id]["outputs"]
                    break
                if status.get("status_str") == "error":
                    print("ERROR", tag, status.get("messages"), flush=True)
                    break
        if not outputs:
            print("FAIL/TIMEOUT", tag, flush=True)
            continue
        elapsed = time.time() - started
        for value in outputs.values():
            for item in value.get("images", []):
                produced = os.path.join(args.comfy_out, item.get("subfolder", ""), item["filename"])
                target = os.path.join(args.outdir, tag + "_" + item["filename"])
                if os.path.exists(produced):
                    shutil.copy2(produced, target)
                    print("%6.1fs  %s" % (elapsed, target), flush=True)


if __name__ == "__main__":
    main()
