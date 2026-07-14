# mypy: ignore-errors


import datetime
import json
from pathlib import Path

import click

from src.core.browser import DESKTOP_UA, DESKTOP_VIEWPORT, Browser
from src.core.db import SessionLocal, init_db
from src.core.session import SessionManager
from src.models import PublishQueue

# ── DOM selectors for Xiaohongshu creator publish page ──────────────────
# The publish form is loaded as a QianKun micro-app after clicking the
# "发布笔记" button.  Run with --explore to dump the page HTML.
# NOTE: title/content/tag fields appear ONLY after images are uploaded.

SEL_PUBLISH_TRIGGER = "text=发布笔记"
SEL_PUBLISH_TAB_TEXTPHOTO = "text=上传图文"
SEL_PUBLISH_BTN = "button:has-text('发布')"
SEL_IMAGE_INPUT = "input.upload-input, input[type=file]"
SEL_TITLE = "input[placeholder*=标题], #title, [class*=title] input"
SEL_CONTENT = "[contenteditable], .DraftEditor-editorContainer, [class*=ql-editor]"
SEL_TAG_INPUT = 'input[placeholder*=标签], input[placeholder*="#"], [class*=tag] input'

SCREENSHOT_DIR = Path("./data/screenshots")


def _ensure_test_image() -> str:
    """Create a minimal valid PNG for dry-run form testing."""
    path = SCREENSHOT_DIR / "test_image.png"
    if path.exists():
        return str(path)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    # Minimal 1x1 red PNG
    import struct
    import zlib

    raw = b""
    for y in range(960):
        raw += b"\x00" + b"\xff\x64\x64" * 720
    compressed = zlib.compress(raw)
    ihdr_data = struct.pack(">IIBBBBB", 720, 960, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + ihdr_data
        + ihdr_crc
        + struct.pack(">I", len(compressed))
        + b"IDAT"
        + compressed
        + idat_crc
        + struct.pack(">I", 0)
        + b"IEND"
        + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    )
    path.write_bytes(png)
    click.echo(f"  Created test image ({len(png) // 1024}KB): {path}")
    return str(path)


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
    try:
        tab = page.locator(SEL_PUBLISH_TAB_TEXTPHOTO).first
        tab.wait_for(state="attached", timeout=10000)
        page.evaluate("(el) => el.click()", tab.element_handle())
    except Exception:
        page.evaluate(
            """() => {
            const spans = document.querySelectorAll('span.title');
            for (const s of spans) {
                if (s.textContent.includes('上传图文')) {
                    s.click();
                    break;
                }
            }
        }"""
        )

    page.wait_for_timeout(2000)
    click.echo("  Tab selected.")


def _upload_images(page, draft_data: dict) -> None:
    """Upload images for the post. Creates a test image if none provided."""
    images = draft_data.get("images", [])
    if not images:
        click.echo("  No images in draft — using test image for form testing.")
        images = [_ensure_test_image()]

    image_paths = []
    for img in images:
        p = Path(img)
        if p.exists():
            image_paths.append(str(p.resolve()))
        elif img.startswith(("http://", "https://")):
            click.echo(f"  Downloading remote image: {img}")
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            import urllib.request

            dest = SCREENSHOT_DIR / f"remote_{len(image_paths)}_{Path(img).name}"
            urllib.request.urlretrieve(img, dest)
            image_paths.append(str(dest))
        else:
            click.echo(f"  Warning: image not found, skipping: {img}")

    if not image_paths:
        click.echo("  No valid images to upload — using test image.")
        image_paths = [_ensure_test_image()]

    click.echo(f"  Uploading {len(image_paths)} image(s)...")
    with page.expect_event("filechooser", timeout=10000) as fc_info:
        page.locator("text=上传图片").first.click()
    file_chooser = fc_info.value
    file_chooser.set_files(image_paths)
    click.echo("  Waiting for image upload to complete...")
    page.wait_for_timeout(5000)
    click.echo("  Images uploaded.")


def _fill_form(page, draft_data: dict) -> None:
    """Fill title and content (tags are inline #hashtags in content)."""
    title = draft_data.get("title", "")
    content = draft_data.get("content", "")

    if title:
        click.echo(f"  Filling title: {title[:50]}...")
        try:
            el = page.wait_for_selector(SEL_TITLE, timeout=15000)
            el.click()
            el.fill(title)
        except Exception as e:
            click.echo(f"  Warning: title input not found ({e})")
    else:
        click.echo("  No title provided.")

    if content:
        click.echo(f"  Filling content ({len(content)} chars)...")
        try:
            el = page.wait_for_selector(SEL_CONTENT, timeout=8000)
            el.click()
            page.keyboard.insert_text(content)
        except Exception as e:
            click.echo(f"  Warning: content editor not found ({e})")
    else:
        click.echo("  No content provided.")

    click.echo("Form filled.")


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

    browser = Browser()
    browser.start(headless=headless)
    ctx = browser.session_context(
        account,
        viewport=DESKTOP_VIEWPORT,
        user_agent=DESKTOP_UA,
    )
    page = ctx.new_page()

    _open_publish_form(page)
    _upload_images(page, draft_data)
    _fill_form(page, draft_data)

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
            click.echo("Published!")
        except Exception as e:
            click.echo(f"  Publish failed: {e}")
            browser.close()
            return False

    browser.close()
    return True


def _explore_page(account: str = "main") -> None:
    """Open the publish page, open form, dump DOM for debugging."""
    session = SessionManager(account)
    if not session.has_session():
        click.echo(f"No session for '{account}'. Run login.py first.")
        return

    browser = Browser()
    browser.start(headless=False)
    ctx = browser.session_context(
        account,
        viewport=DESKTOP_VIEWPORT,
        user_agent=DESKTOP_UA,
    )
    page = ctx.new_page()

    _open_publish_form(page)

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    html = page.content()
    dump_path = SCREENSHOT_DIR / "page_with_form.html"
    dump_path.write_text(html)
    click.echo(f"Page HTML saved to: {dump_path}")

    page.screenshot(path=str(SCREENSHOT_DIR / "publish_form.png"), full_page=True)
    click.echo(f"Screenshot saved to: {SCREENSHOT_DIR / 'publish_form.png'}")

    for name, sel in [
        ("publish trigger", SEL_PUBLISH_TRIGGER),
        ("image input", SEL_IMAGE_INPUT),
        ("title", SEL_TITLE),
        ("content", SEL_CONTENT),
        ("tag input", SEL_TAG_INPUT),
        ("publish btn", SEL_PUBLISH_BTN),
    ]:
        els = page.query_selector_all(sel)
        click.echo(f"  {name}: {len(els)} match(es)")
        for el in els[:3]:
            info = el.evaluate("el => el.tagName + (el.className ? '.' + el.className : '')")
            click.echo(f"    -> <{info}> visible={el.is_visible()}")

    all_els = page.query_selector_all("button, input, [contenteditable], [role=textbox]")
    click.echo(f"\n  All interactive ({len(all_els)}):")
    for el in all_els[:30]:
        tag = el.evaluate("el => el.tagName")
        text = el.evaluate(
            "el => (el.tagName==='BUTTON' ? el.textContent.trim() : '') "
            "|| el.getAttribute('placeholder') || el.getAttribute('aria-label') || ''"
        )
        if text or tag == "INPUT":
            click.echo(f"    <{tag}> visible={el.is_visible()} text='{text[:40]}'")

    browser.close()


@click.command()
@click.option("--draft", type=click.Path(exists=True), help="Draft JSON file to publish")
@click.option("--queue-id", type=int, help="Queue item ID to publish")
@click.option("--account", default="main", help="Account name for session")
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser headless (default: headless). Pass --no-headless to see the browser.",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Fill form only, no submit (default: dry-run).",
)
@click.option(
    "--explore",
    is_flag=True,
    help="Open publish form and dump DOM for debugging selectors",
)
def main(draft, queue_id, account, headless, dry_run, explore) -> None:
    """Publish a post to Xiaohongshu immediately.

    By default runs in *dry-run* mode (form filled + screenshot, no submit).
    Pass ``--no-dry-run`` to actually publish.
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
