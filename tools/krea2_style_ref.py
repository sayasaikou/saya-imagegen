# -*- coding: utf-8 -*-
"""Krea 2 style-reference generation: one prompt, several reference images, same seed.

Purpose: find out which reference image actually carries the style you want, instead of
guessing from one. Use the same prompt and seed so the only variable is the reference.

Usage:
    python krea2_style_ref.py --refs-dir <dir> --ref ref1.png --ref ref2.png \
        --comfy-in <ComfyUI input dir> --comfy-out <ComfyUI output dir> --outdir <dir>

The script stages each reference into the ComfyUI input directory, runs the style-reference
workflow through the API, and copies every result into --outdir.
"""
import argparse
import json
import os
import shutil
import time
import urllib.request


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--refs-dir", required=True)
    p.add_argument("--ref", action="append", required=True, help="reference image file name; repeatable")
    p.add_argument("--comfy-in", required=True)
    p.add_argument("--comfy-out", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--host", default="http://127.0.0.1:8188")
    p.add_argument("--prompt", required=True)
    p.add_argument("--width", type=int, default=2048)
    p.add_argument("--height", type=int, default=1152)
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=20261018)
    p.add_argument("--unet", default="krea2_turbo_int8_convrot.safetensors")
    p.add_argument("--clip", default="qwen3vl_4b_int8_convrot.safetensors")
    p.add_argument("--vae", default="qwen_image_vae.safetensors")
    p.add_argument("--lora", default="krea2_style_reference.safetensors")
    p.add_argument("--lora-strength", type=float, default=1.0)
    return p.parse_args()


def post(host, path, payload):
    req = urllib.request.Request(host + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())


def get(host, path):
    return json.loads(urllib.request.urlopen(host + path, timeout=120).read().decode())


def build(a, name, image_name):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": a.unet, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": a.clip, "type": "krea2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": a.vae}},
        "4": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"lora_name": a.lora, "strength_model": a.lora_strength, "model": ["1", 0]}},
        "5": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "6": {"class_type": "TextEncodeQwenImageEditPlus",
              "inputs": {"clip": ["2", 0], "prompt": a.prompt, "vae": ["3", 0], "image1": ["5", 0]}},
        "7": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["6", 0]}},
        "8": {"class_type": "FluxKontextMultiReferenceLatentMethod",
              "inputs": {"conditioning": ["6", 0], "reference_latents_method": "index_timestep_zero"}},
        "9": {"class_type": "ModelSamplingFlux",
              "inputs": {"model": ["4", 0], "max_shift": 1.15, "base_shift": 0.5,
                         "width": a.width, "height": a.height}},
        "10": {"class_type": "CFGGuider",
               "inputs": {"model": ["9", 0], "positive": ["8", 0], "negative": ["7", 0], "cfg": a.cfg}},
        "11": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "12": {"class_type": "BasicScheduler",
               "inputs": {"model": ["9", 0], "scheduler": "simple", "steps": a.steps, "denoise": 1.0}},
        "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": a.seed}},
        "14": {"class_type": "EmptyLatentImage",
               "inputs": {"width": a.width, "height": a.height, "batch_size": 1}},
        "15": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["13", 0], "guider": ["10", 0], "sampler": ["11", 0],
                          "sigmas": ["12", 0], "latent_image": ["14", 0]}},
        "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["3", 0]}},
        "17": {"class_type": "SaveImage", "inputs": {"filename_prefix": name, "images": ["16", 0]}},
    }


def run(a, name, image_name):
    started = time.time()
    try:
        response = post(a.host, "/prompt", {"prompt": build(a, name, image_name)})
    except Exception as exc:  # noqa: BLE001
        body = exc.read().decode() if hasattr(exc, "read") else str(exc)
        print("SUBMIT FAIL", name, body[:600], flush=True)
        return False
    prompt_id = response["prompt_id"]
    print("submit", name, prompt_id, flush=True)
    while time.time() - started < 1800:
        time.sleep(2)
        history = get(a.host, "/history/" + prompt_id)
        if prompt_id in history:
            status = history[prompt_id].get("status", {})
            if status.get("completed"):
                break
            if status.get("status_str") == "error":
                print("ERROR", name, status.get("messages"), flush=True)
                return False
    else:
        print("TIMEOUT", name, flush=True)
        return False

    os.makedirs(a.outdir, exist_ok=True)
    for value in history[prompt_id]["outputs"].values():
        for item in value.get("images", []):
            produced = os.path.join(a.comfy_out, item.get("subfolder", ""), item["filename"])
            target = os.path.join(a.outdir, item["filename"])
            if os.path.exists(produced):
                shutil.copy2(produced, target)
                print("%.1fs\t%s" % (time.time() - started, target), flush=True)
    return True


def main():
    args = parse_args()
    os.makedirs(args.comfy_in, exist_ok=True)
    for index, ref in enumerate(args.ref):
        source = os.path.join(args.refs_dir, ref)
        if not os.path.exists(source):
            print("missing reference:", source, flush=True)
            continue
        tag = "r%d" % index
        staged = "sr_%s_%s" % (tag, os.path.splitext(ref)[0].replace(" ", "_"))
        staged += ".png" if not staged.lower().endswith(".png") else ""
        shutil.copy2(source, os.path.join(args.comfy_in, staged))
        run(args, "sr_%s" % tag, staged)


if __name__ == "__main__":
    main()
