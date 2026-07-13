# mypy: ignore-errors
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


@click.command()
@click.option("--input", "-i", type=click.Path(exists=True), help="Input draft JSON file")
@click.option("--category", "-c", help="Content category (food/travel/digital)")
@click.option("--output", "-o", type=click.Path(), help="Output spec file")
@click.option("--list-specs", is_flag=True, help="List available image specs")
def main(  # type: ignore[no-untyped-def]
    input, category, output, list_specs
) -> None:
    """Generate image specs for post content."""
    if list_specs:
        for cat, spec in IMAGE_SPECS.items():
            click.echo(f"\n[{cat}]")
            for k, v in spec.items():
                click.echo(f"  {k}: {v}")
        return

    draft = {}
    if input:
        with open(input) as f:
            draft = json.load(f)
        category = category or draft.get("category") or draft.get("template", "")

    spec = IMAGE_SPECS.get(
        category,
        {
            "style": "清晰美观,符合平台调性",
            "composition": "多角度拍摄",
            "count": 6,
            "notes": "参考同品类爆款图片风格",
        },
    )

    result = {
        "category": category or "general",
        "title": draft.get("title", ""),
        "image_spec": spec,
        "image_prompts": [
            f"{draft.get('title', '')} - 场景{i + 1}: {spec['style']}, {spec['composition']}"
            for i in range(int(spec["count"]))
        ],
        "created_at": datetime.now().isoformat(),
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
