# mypy: ignore-errors


import datetime
import json
from pathlib import Path

import click

from src.core.browser import Browser
from src.core.db import SessionLocal, init_db
from src.core.session import SessionManager
from src.models import PublishQueue

# ── DOM selectors for Xiaohongshu creator publish page ──────────────────
# These are based on the current creator.xiaohongshu.com/publish DOM.
# If the page layout changes, update these constants.
# Run with --explore to dump the page structure for debugging.

SEL_IMAGE_INPUT = "input[type=file]"
SEL_TITLE = "input[placeholder*=标题], #title, [class*=title] input"
SEL_CONTENT = "[contenteditable], .DraftEditor-editorContainer, [class*=ql-editor]"
SEL_TAG_INPUT = "input[placeholder*=标签], input[placeholder*=#], [class*=tag] input"
SEL_PUBLISH_BTN = "button:has-text('发布')"
SEL_UPLOAD_AREA = ".upload-container, [class*=upload], [class*=dropzone]"

SCREENSHOT_DIR = Path("./data/screenshots")


def _ensure_images(images: list[str]) -> list[str]:
    """Resolve image paths, downloading remote URLs if needed."""
    resolved = []
    for img in images or []:
        p = Path(img)
        if p.exists():
            resolved.append(str(p.resolve()))
        elif img.startswith(("http://", "https://")):
            click.echo(f"  Downloading remote image: {img}")
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            import urllib.request

            dest = SCREENSHOT_DIR / f"remote_{len(resolved)}_{Path(img).name}"
            urllib.request.urlretrieve(img, dest)
            resolved.append(str(dest))
        else:
            click.echo(f"  Warning: image not found, skipping: {img}")
    return resolved


def _fill_form(page, draft_data: dict, dry_run: bool) -> None:
    """Fill the Xiaohongshu publish form with draft data."""
    title = draft_data.get("title", "")
    content = draft_data.get("content", "")
    tags = draft_data.get("tags", [])
    images = draft_data.get("images", [])

    # ── 1. Upload images ────────────────────────────────────────────────
    if images:
        image_paths = _ensure_images(images)
        if image_paths:
            click.echo(f"  Uploading {len(image_paths)} image(s)...")
            file_chooser = page.wait_for_event("filechooser", timeout=10000)
            page.click(SEL_UPLOAD_AREA)
            file_chooser.set_files(image_paths)
            page.wait_for_timeout(2000)
            click.echo("  Images uploaded.")
    else:
        click.echo("  No images provided — skipping upload.")

    # ── 2. Fill title ───────────────────────────────────────────────────
    if title:
        click.echo(f"  Filling title: {title}")
        title_el = page.wait_for_selector(SEL_TITLE, timeout=10000)
        title_el.click()
        title_el.fill(title)
    else:
        click.echo("  No title provided.")

    # ── 3. Fill content ─────────────────────────────────────────────────
    if content:
        click.echo(f"  Filling content ({len(content)} chars)...")
        content_el = page.wait_for_selector(SEL_CONTENT, timeout=10000)
        content_el.click()
        page.keyboard.insert_text(content)
    else:
        click.echo("  No content provided.")

    # ── 4. Add tags ─────────────────────────────────────────────────────
    if tags:
        click.echo(f"  Adding {len(tags)} tag(s): {', '.join(tags)}")
        tag_el = page.wait_for_selector(SEL_TAG_INPUT, timeout=10000)
        for tag in tags:
            tag_el.click()
            tag_el.fill(tag)
            page.keyboard.press("Enter")
            page.wait_for_timeout(300)
    else:
        click.echo("  No tags provided.")

    click.echo("Form filled successfully.")


def _publish_via_browser(
    draft_data: dict,
    account: str = "main",
    headless: bool = False,
    dry_run: bool = True,
) -> bool:
    """Publish (or dry-run) a post by automating the Xiaohongshu creator page.

    When *dry_run* is True (default), the form is filled but the publish
    button is never clicked — a screenshot is saved instead.
    """
    session = SessionManager(account)
    if not session.has_session():
        click.echo(f"No session for '{account}'. Run login.py first.")
        return False

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    with Browser() as browser:
        ctx = browser.session_context(account)
        page = ctx.new_page()

        click.echo("Opening Xiaohongshu creator publish page...")
        page.goto("https://creator.xiaohongshu.com/publish")

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        _fill_form(page, draft_data, dry_run)

        if dry_run:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = SCREENSHOT_DIR / f"dry_run_{timestamp}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            click.echo(f"[DRY-RUN] Publish skipped. Screenshot saved: {screenshot_path}")
            click.echo(f"[DRY-RUN] Would publish: {draft_data.get('title', 'Untitled')}")
        else:
            click.echo("  Clicking publish button...")
            page.click(SEL_PUBLISH_BTN)
            page.wait_for_selector("text=发布成功", timeout=30000)
            click.echo("Published successfully!")

    return True


def _explore_page(account: str = "main") -> None:
    """Open the publish page and print the DOM structure for debugging."""
    session = SessionManager(account)
    if not session.has_session():
        click.echo(f"No session for '{account}'. Run login.py first.")
        return

    with Browser() as browser:
        ctx = browser.session_context(account)
        page = ctx.new_page()

        click.echo("Opening Xiaohongshu creator publish page...")
        page.goto("https://creator.xiaohongshu.com/publish")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        html = page.content()
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        dump_path = SCREENSHOT_DIR / "page_dump.html"
        dump_path.write_text(html)
        click.echo(f"Page HTML saved to: {dump_path}")

        page.screenshot(path=str(SCREENSHOT_DIR / "page_screenshot.png"), full_page=True)
        click.echo(f"Screenshot saved to: {SCREENSHOT_DIR / 'page_screenshot.png'}")

        for name, sel in [
            ("image input", SEL_IMAGE_INPUT),
            ("title", SEL_TITLE),
            ("content", SEL_CONTENT),
            ("tag input", SEL_TAG_INPUT),
            ("publish btn", SEL_PUBLISH_BTN),
            ("upload area", SEL_UPLOAD_AREA),
        ]:
            els = page.query_selector_all(sel)
            click.echo(f"  {name} ('{sel}'): {len(els)} match(es)")
            for el in els[:3]:
                info = el.evaluate("el => el.tagName + (el.className ? '.' + el.className : '')")
                visible = el.is_visible()
                click.echo(f"    -> <{info}> visible={visible}")


@click.command()
@click.option("--draft", type=click.Path(exists=True), help="Draft JSON file to publish")
@click.option("--queue-id", type=int, help="Queue item ID to publish")
@click.option("--account", default="main", help="Account name for session")
@click.option("--headless", is_flag=True, help="Run browser headless")
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Fill form only, no submit. Pass --no-dry-run to publish.",
)
@click.option(
    "--explore",
    is_flag=True,
    help="Open publish page and dump DOM structure for debugging selectors",
)
def main(draft, queue_id, account, headless, dry_run, explore) -> None:
    """Publish a post to Xiaohongshu immediately.

    By default this runs in *dry-run* mode: the form is filled and a
    screenshot is saved, but nothing is actually published. Pass
    ``--no-dry-run`` to submit.
    """
    if explore:
        _explore_page(account)
        return

    init_db()
    db = SessionLocal()

    draft_data = None

    if queue_id:
        item = db.query(PublishQueue).filter(PublishQueue.id == queue_id).first()
        if not item:
            click.echo(f"Queue item {queue_id} not found")
            db.close()
            return
        draft_data = {
            "title": item.title,
            "content": item.content or "",
            "tags": json.loads(item.tags) if item.tags else [],
            "images": json.loads(item.images) if item.images else [],
        }
        click.echo(f"Publishing from queue: {item.title}")
    elif draft:
        with open(draft) as f:
            draft_data = json.load(f)
        click.echo(f"Publishing draft: {draft_data.get('title', 'Untitled')}")
    else:
        click.echo("Provide --draft, --queue-id, or --explore")
        db.close()
        return

    success = _publish_via_browser(draft_data, account, headless, dry_run=dry_run)

    if queue_id and success and not dry_run:
        item = db.query(PublishQueue).filter(PublishQueue.id == queue_id).first()
        if item:
            item.status = "published"
            item.published_at = datetime.datetime.now()
            db.commit()
            click.echo(f"Queue item {queue_id} marked as published")

    db.close()


if __name__ == "__main__":
    main()
