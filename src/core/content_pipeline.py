"""Brief → finalize → publish-ready draft helpers for the create pipeline."""

from __future__ import annotations

import re
from typing import Any

# Quality gates from SKILL_content_creation.md
TITLE_MAX_CHARS = 20
BODY_MIN_CHARS = 200
BODY_MAX_CHARS = 800
TAGS_MIN = 5
TAGS_MAX = 10
IMAGES_MIN = 3
IMAGES_MAX = 9


def _generated_block(data: dict[str, Any]) -> dict[str, Any]:
    gen = data.get("generated")
    if isinstance(gen, dict):
        return gen
    return {}


def extract_post_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize brief or already-finalized draft into title/body/tags/images."""
    gen = _generated_block(data)
    title = str(data.get("title") or gen.get("title") or "").strip()
    body = str(data.get("content") or data.get("body") or gen.get("body") or "").strip()
    tags_raw = data.get("tags") if data.get("tags") is not None else gen.get("tags")
    tags: list[str] = []
    if isinstance(tags_raw, list):
        tags = [str(t).strip().lstrip("#") for t in tags_raw if str(t).strip()]
    elif isinstance(tags_raw, str) and tags_raw.strip():
        tags = [t.strip().lstrip("#") for t in tags_raw.replace(",", " ").split() if t.strip()]

    images = data.get("images") or gen.get("images") or []
    if not isinstance(images, list):
        images = []

    image_specs = data.get("image_specs") or gen.get("image_specs") or []
    if not isinstance(image_specs, list):
        image_specs = []

    return {
        "title": title,
        "body": body,
        "tags": tags,
        "images": [str(i) for i in images],
        "image_specs": image_specs,
        "meta": data.get("meta") if isinstance(data.get("meta"), dict) else {},
    }


def append_hashtags(body: str, tags: list[str]) -> str:
    """Ensure tags appear as inline #hashtags at the end of body (XHS convention)."""
    existing = {m.group(1) for m in re.finditer(r"#([^\s#]+)", body)}
    missing = [t for t in tags if t and t not in existing]
    if not missing:
        return body
    suffix = " ".join(f"#{t}" for t in missing)
    if body and not body.endswith("\n"):
        body += "\n"
    return f"{body}\n{suffix}".strip()


def validate_post(
    fields: dict[str, Any],
    *,
    require_images: bool = False,
) -> list[str]:
    """Return human-readable violation messages (empty => OK)."""
    issues: list[str] = []
    title = fields.get("title") or ""
    body = fields.get("body") or ""
    tags = fields.get("tags") or []
    images = fields.get("images") or []

    if not title:
        issues.append("title is empty")
    elif len(title) > TITLE_MAX_CHARS:
        issues.append(f"title length {len(title)} > {TITLE_MAX_CHARS}")

    body_len = len(body.replace("#", "").strip())
    # count body without trailing hashtag block roughly
    body_core = re.sub(r"(?:\s*#[^\s#]+)+\s*$", "", body).strip()
    core_len = len(body_core)
    if core_len < BODY_MIN_CHARS:
        issues.append(f"body length {core_len} < {BODY_MIN_CHARS}")
    elif core_len > BODY_MAX_CHARS:
        issues.append(f"body length {core_len} > {BODY_MAX_CHARS}")

    if len(tags) < TAGS_MIN:
        issues.append(f"tags count {len(tags)} < {TAGS_MIN}")
    elif len(tags) > TAGS_MAX:
        issues.append(f"tags count {len(tags)} > {TAGS_MAX}")

    if require_images:
        n = len(images)
        if n < IMAGES_MIN:
            issues.append(f"images count {n} < {IMAGES_MIN}")
        elif n > IMAGES_MAX:
            issues.append(f"images count {n} > {IMAGES_MAX}")

    if "\n\n" not in body_core and core_len >= BODY_MIN_CHARS:
        issues.append("body has no blank line between paragraphs")

    del body_len  # silence unused if only core_len used
    return issues


def build_publish_draft(
    data: dict[str, Any],
    *,
    images: list[str] | None = None,
    image_specs: list[Any] | None = None,
) -> dict[str, Any]:
    """Build a schedule_post / publish_now compatible draft dict."""
    fields = extract_post_fields(data)
    if images is not None:
        fields["images"] = [str(i) for i in images]
    if image_specs is not None:
        fields["image_specs"] = image_specs

    content = append_hashtags(fields["body"], fields["tags"])
    return {
        "title": fields["title"],
        "content": content,
        "tags": fields["tags"],
        "images": fields["images"],
        "image_specs": fields["image_specs"],
        "meta": fields["meta"],
        "status": "final",
    }
