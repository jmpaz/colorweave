import os
from anthropic import AnthropicBedrock
from c_weave.utils.color import estimate_colors


def generate_palette(colors, model="sonnet"):
    client = AnthropicBedrock(
        aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_region="us-east-1",
    )

    named_colors = estimate_colors(colors)
    colors_str = list(zip(colors, named_colors))
    prompt = open("data/prompts/palette_design/base.md").read()
    command = f"<cmd>/design [{colors_str}]</cmd>"

    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "Understood; awaiting command."},
        {"role": "user", "content": command},
    ]

    model_map = {
        "instant": "anthropic.claude-instant-v1",
        "haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    }

    output = client.messages.create(
        model=model_map[model], max_tokens=512, messages=messages
    )

    return output.content[0].text
