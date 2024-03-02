from comfy_bridge.client import Generation


def generate_wallpaper(colors: str):
    params = {
        "prompt": f"a beautiful landscape, {colors} palette",
        "prompt_negative": "poor quality",
        "width": 1365,
        "height": 768,
        "use_refiner": False,
        "sampler": "euler",
        "scheduler": "normal",
        "steps": 30,
        "cfg": 8.5,
        "seed": None,
        "loras": None,
        "workflow_path": "data/workflows/sdxl-lora.json",
    }

    gen = Generation(**params)
    return gen.output
