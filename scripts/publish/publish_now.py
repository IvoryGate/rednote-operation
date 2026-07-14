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
# The publish form is loaded as a QianKun micro-app after clicking the
# "发布笔记" button.  Run with --explore to dump the page HTML after
# the form has loaded.

SEL_PUBLISH_TRIGGER = "text=发布笔记"
SEL_PUBLISH_TAB_TEXTPHOTO = "text=上传图文"
SEL_PUBLISH_BTN = "button:has-text('发布')"
SEL_IMAGE_INPUT = "input.upload-input, input[type=file]"
SEL_UPLOAD_AREA = ".upload-container, [class*=upload], [class*=dropzone]"
SEL_TITLE = "input[placeholder*=标题], #title, [class*=title] input"
SEL_CONTENT = "[contenteditable], .DraftEditor-editorContainer, [class*=ql-editor]"
SEL_TAG_INPUT = 'input[placeholder*=标签], input[placeholder*="#"], [class*=tag] input'

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


def _open_publish_form(page) -> None:
    """Navigate to creator platform and open the publish form."""
    page.goto("https://creator.xiaohongshu.com/publish", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    click.echo("  Clicking '发布笔记' to open publish form...")
    trigger = page.locator(SEL_PUBLISH_TRIGGER).first
    trigger.wait_for(state="visible", timeout=15000)
    trigger.click()

    page.wait_for_timeout(2000)

    click.echo("  Selecting '上传图文' tab...")
    tab = page.locator(SEL_PUBLISH_TAB_TEXTPHOTO).first
    tab.wait_for(state="attached", timeout=10000)
    tab.click(force=True)

    page.wait_for_timeout(3000)
    click.echo("  Waiting for publish form to load...")


def _fill_form(page, draft_data: dict, dry_run: bool) -> bool:
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
        click.echo(f"  Filling title: {title[:50]}...")
        try:
            title_el = page.wait_for_selector(SEL_TITLE, timeout=8000)
            title_el.click()
            title_el.fill(title)
        except Exception as e:
            click.echo(f"  Warning: could not fill title ({e})")
    else:
        click.echo("  No title provided.")

    # ── 3. Fill content ─────────────────────────────────────────────────
    if content:
        click.echo(f"  Filling content ({len(content)} chars)...")
        try:
            content_el = page.wait_for_selector(SEL_CONTENT, timeout=8000)
            content_el.click()
            page.keyboard.insert_text(content)
        except Exception as e:
            click.echo(f"  Warning: could not fill content ({e})")
    else:
        click.echo("  No content provided.")

    # ── 4. Add tags ─────────────────────────────────────────────────────
    if tags:
        click.echo(f"  Adding {len(tags)} tag(s): {', '.join(tags)}")
        try:
            tag_el = page.wait_for_selector(SEL_TAG_INPUT, timeout=8000)
            for tag in tags:
                tag_el.click()
                tag_el.fill(tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(300)
        except Exception as e:
            click.echo(f"  Warning: could not add tags ({e})")
    else:
        click.echo("  No tags provided.")

    click.echo("Form filled successfully.")
    return True


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

        _open_publish_form(page)
        _fill_form(page, draft_data, dry_run)

        if dry_run:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = SCREENSHOT_DIR / f"dry_run_{timestamp}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            click.echo(f"[DRY-RUN] Skipped publish. Screenshot: {screenshot_path}")
        else:
            click.echo("  Clicking publish button...")
            try:
                page.click(SEL_PUBLISH_BTN)
                page.wait_for_selector("text=发布成功", timeout=30000)
                click.echo("Published successfully!")
            except Exception as e:
                click.echo(f"  Publish failed: {e}")
                return False

    return True


def _explore_page(account: str = "main") -> None:
    """Open the publish page, click the trigger, dump DOM for debugging."""
    session = SessionManager(account)
    if not session.has_session():
        click.echo(f"No session for '{account}'. Run login.py first.")
        return

    with Browser() as browser:
        ctx = browser.session_context(account)
        page = ctx.new_page()

        _open_publish_form(page)

        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

        html = page.content()
        dump_path = SCREENSHOT_DIR / "page_with_form.html"
        dump_path.write_text(html)
        click.echo(f"Page HTML (form loaded) saved to: {dump_path}")

        page.screenshot(path=str(SCREENSHOT_DIR / "publish_form.png"), full_page=True)
        click.echo(f"Screenshot saved to: {SCREENSHOT_DIR / 'publish_form.png'}")

        for name, sel in [
            ("publish trigger", SEL_PUBLISH_TRIGGER),
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

        # Also dump all buttons and inputs for discovery
        all_buttons = page.query_selector_all("button, input, [contenteditable], [role=textbox]")
        click.echo(f"\n  All interactive elements ({len(all_buttons)} found):")
        for el in all_buttons[:30]:
            tag = el.evaluate("el => el.tagName")
            text = el.evaluate(
                "el => (el.tagName==='BUTTON' ? el.textContent.trim() : '') "
                "|| el.getAttribute('placeholder') || el.getAttribute('aria-label') || ''"
            )
            visible = el.is_visible()
            if text or tag == "INPUT":
                click.echo(f"    <{tag}> visible={visible} text='{text[:40]}'")


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
    help="Open publish form and dump DOM for debugging selectors",
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
