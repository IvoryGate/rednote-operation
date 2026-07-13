import json
from datetime import datetime
from pathlib import Path

import click

IMAGE_SPECS = {
    "food": {
        "style": "明亮诱人,暖色调,突出食物细节",
        "composition": "俯拍45度,浅景深",
        "count": 6,
        "notes": "首图为成品全景,后续为步骤/细节",
    },
    "travel": {
        "style": "自然风光,明亮通透,电影感色调",
        "composition": "广角+中景交替",
        "count": 9,
        "notes": "首图为标志性景观,包含人景互动",
    },
    "digital": {
        "style": "简约干净,质感强烈,偏冷色调",
        "composition": "特写+场景图交替",
        "count": 6,
        "notes": "首图为产品外观,包含使用场景图",
    },
}


def _load_brief(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _extract_image_guidance(template_text: str) -> list[str]:
    """Parse image suggestions from a template section."""
    lines = template_text.splitlines()
    capturing = False
    specs = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### ") and "图片" in stripped:
            capturing = True
            continue
        if capturing:
            if stripped.startswith("### ") or stripped.startswith("## "):
                break
            if stripped and (stripped[0].isdigit() or stripped.startswith("-")):
                specs.append(stripped.lstrip("0123456789. -"))
    return specs


@click.command()
@click.option("--brief", "-b", type=click.Path(exists=True), help="Input brief JSON file")
@click.option("--category", "-c", help="Content category (food/travel/digital)")
@click.option("--topic", help="Post topic (used without --brief)")
@click.option("--output", "-o", type=click.Path(), help="Output spec file")
@click.option("--list-specs", is_flag=True, help="List available image specs")
def main(brief, category, topic, output, list_specs):  # type: ignore[no-untyped-def]
    """Generate image specs for post content.

    Reads a brief JSON (from generate_post.py) and produces
    per-slide image prompts and composition guidance.
    """
    if list_specs:
        for cat, spec in IMAGE_SPECS.items():
            click.echo(f"\n[{cat}]")
            for k, v in spec.items():
                click.echo(f"  {k}: {v}")
        return

    if brief:
        data = _load_brief(brief)
        meta = data.get("meta", {})
        topic = topic or meta.get("topic", "")
        category = category or meta.get("category", "")
        template_text = data.get("template", "")
    else:
        template_text = ""
        if not topic:
            raise click.ClickException("Provide --topic (or --brief)")

    category = category or "general"

    spec = IMAGE_SPECS.get(
        category,
        {"style": "清晰美观,符合平台调性", "composition": "多角度拍摄", "count": 6, "notes": ""},
    )

    image_guidance = _extract_image_guidance(template_text) or [spec["notes"]]

    count = int(spec["count"])
    image_prompts = []
    for i in range(count):
        guidance = image_guidance[i] if i < len(image_guidance) else spec["notes"]
        image_prompts.append(
            f"{topic} - 图{i + 1}: {guidance} | 风格: {spec['style']} | 构图: {spec['composition']}"
        )

    result = {
        "meta": {"topic": topic, "category": category, "created_at": datetime.now().isoformat()},
        "image_spec": spec,
        "image_guidance": image_guidance,
        "image_prompts": image_prompts,
    }

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        click.echo(f"Image specs saved to {path}")
    else:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
