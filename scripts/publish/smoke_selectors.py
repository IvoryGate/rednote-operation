"""Offline (and optional live) publish selector smoke checks.

Offline mode validates ``config/publish_selectors.yaml`` shape and that every
control has at least one strategy. Live mode requires a saved session and opens
the creator publish page to probe selectors that exist before image upload.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from src.core.publish_dom import (
    SelectorRegistry,
    SelectorResolutionError,
    offline_smoke,
    resolve_locator,
)
from src.core.session import SessionManager


def live_smoke(account: str, headless: bool) -> list[str]:
    """Open creator publish page and try resolving key controls."""
    from src.core.browser import DESKTOP_UA, DESKTOP_VIEWPORT, Browser

    problems: list[str] = []
    session = SessionManager(account)
    if not session.has_session():
        return [f"no session for '{account}' — run login first"]

    registry = SelectorRegistry.load()
    browser = Browser()
    browser.start(headless=headless)
    try:
        ctx = browser.session_context(
            account,
            viewport=DESKTOP_VIEWPORT,
            user_agent=DESKTOP_UA,
        )
        page = ctx.new_page()
        page.goto("https://creator.xiaohongshu.com/publish", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        for control in ("publish_trigger",):
            try:
                loc = resolve_locator(page, registry, control, timeout_ms=10000)
                loc.click()
                page.wait_for_timeout(1500)
            except SelectorResolutionError as exc:
                problems.append(str(exc))

        # Default landing tab is video (「上传视频」). Switch to image+text
        # before probing upload_images — same flow as publish_now.py.
        try:
            tab = resolve_locator(
                page, registry, "text_photo_tab", timeout_ms=10000, state="attached"
            )
            try:
                page.evaluate("(el) => el.click()", tab.element_handle())
            except Exception:
                tab.click(force=True)
            page.wait_for_timeout(2000)
        except SelectorResolutionError as exc:
            problems.append(str(exc))

        for control in ("upload_images", "image_input"):
            try:
                resolve_locator(page, registry, control, timeout_ms=8000, state="attached")
            except SelectorResolutionError as exc:
                problems.append(str(exc))
    finally:
        browser.close()
    return problems


@click.command()
@click.option("--live", is_flag=True, help="Open creator page and probe selectors")
@click.option("--account", default="main", show_default=True)
@click.option("--headless/--no-headless", default=True)
@click.option("--json-out", type=click.Path(), help="Write machine-readable result JSON")
def main(live: bool, account: str, headless: bool, json_out: str | None) -> None:
    """Run publish selector smoke checks."""
    registry = SelectorRegistry.load()
    problems = offline_smoke(registry)
    mode = "offline"
    if live:
        mode = "live"
        problems.extend(live_smoke(account, headless))

    result = {
        "mode": mode,
        "ok": not problems,
        "registry_version": registry.version,
        "last_verified": registry.last_verified,
        "controls": sorted(registry.controls.keys()),
        "problems": problems,
    }

    if json_out:
        path = Path(json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"Wrote {path}")

    if problems:
        click.echo(f"SMOKE FAIL ({mode}): {len(problems)} problem(s)")
        for item in problems:
            click.echo(f"  - {item}")
        raise SystemExit(1)

    click.echo(
        f"SMOKE OK ({mode}): registry v{registry.version} "
        f"last_verified={registry.last_verified} controls={len(registry.controls)}"
    )


if __name__ == "__main__":
    main()
