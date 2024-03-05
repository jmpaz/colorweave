from comfy_bridge.client import Generation, upscale as comfy_upscale


def generate_wallpaper(colors: str):
    """Create an image using comfy_bridge's Generation class."""
    params = {
        "prompt": f"a beautiful landscape, {colors} hues",
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
    return gen.output[0]


def upscale(input_image):
    """Simple wrapper around comfy_bridge's upscale function."""
    params = {
        "steps": "100",
        "pre_downscale": "None",
        "post_downscale": "None",
        "downsample_method": "Lanczos",
    }
    return comfy_upscale(
        input_image,
        params,
        mode="ldsr",
        workflow_path="data/workflows/upscale_ldsr.json",
    )
