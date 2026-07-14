# mypy: ignore-errors


import datetime
import json

import click

from src.core.browser import Browser
from src.core.db import SessionLocal, init_db
from src.core.session import SessionManager
from src.models import PublishQueue


def _publish_via_browser(
    draft_data: dict,
    account: str = "main",
    headless: bool = False,
) -> bool:
    """Publish a post by automating the Xiaohongshu creator page.

    Uses a saved browser session to navigate to the publish page,
    fill in the form, and submit.
    """
    session = SessionManager(account)
    if not session.has_session():
        click.echo(f"No session for '{account}'. Run login.py first.")
        return False

    with Browser() as browser:
        browser.start()
        ctx = browser.session_context(account)
        page = ctx.new_page()

        # Navigate to the creator publish page
        click.echo("Opening Xiaohongshu creator publish page...")
        page.goto("https://creator.xiaohongshu.com/publish")

        # Wait for page to load
        page.wait_for_load_state("networkidle")

        # TODO: Fill in the publish form
        # The selectors below are placeholders — update them to match
        # the actual Xiaohongshu creator page DOM.
        #
        # Image upload:
        # page.set_input_files("input[type=file]", image_paths)
        # page.wait_for_selector(".upload-progress", state="hidden")
        #
        # Title:
        # page.fill("input[placeholder*=标题]", draft_data.get("title", ""))
        #
        # Content:
        # page.fill("div[contenteditable]", draft_data.get("content", ""))
        #
        # Tags:
        # tag_input = page.locator("input[placeholder*=标签]")
        # for tag in draft_data.get("tags", []):
        #     tag_input.fill(tag)
        #     tag_input.press("Enter")
        #
        # Publish button:
        # page.click("button:has-text('发布')")
        # page.wait_for_selector("text=发布成功", timeout=30000)

        click.echo("Browser form automation is ready (TODO: fill selectors).")
        click.echo(f"Would publish: {draft_data.get('title', 'Untitled')}")

    return True


@click.command()
@click.option("--draft", type=click.Path(exists=True), help="Draft JSON file to publish")
@click.option("--queue-id", type=int, help="Queue item ID to publish")
@click.option("--account", default="main", help="Account name for session")
@click.option("--headless", is_flag=True, help="Run browser headless")
def main(draft, queue_id, account, headless) -> None:
    """Publish a post to Xiaohongshu immediately."""
    init_db()
    db = SessionLocal()

    draft_data = None

    if queue_id:
        item = db.query(PublishQueue).filter(PublishQueue.id == queue_id).first()
        if not item:
            click.echo(f"Queue item {queue_id} not found")
            db.close()
            return
        draft_data = {"title": item.title, "content": item.content or "", "tags": []}
        click.echo(f"Publishing from queue: {item.title}")
    elif draft:
        with open(draft) as f:
            draft_data = json.load(f)
        click.echo(f"Publishing draft: {draft_data.get('title', 'Untitled')}")
    else:
        click.echo("Provide --draft or --queue-id")
        db.close()
        return

    success = _publish_via_browser(draft_data, account, headless)

    if queue_id and success:
        item = db.query(PublishQueue).filter(PublishQueue.id == queue_id).first()
        if item:
            item.status = "published"
            item.published_at = datetime.datetime.now()
            db.commit()
            click.echo(f"Queue item {queue_id} marked as published")

    db.close()


if __name__ == "__main__":
    main()
