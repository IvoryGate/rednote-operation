"""Multi-strategy publish-page selector resolution and failure evidence dumps."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

DEFAULT_SELECTORS_PATH = Path("config/publish_selectors.yaml")
DEFAULT_EVIDENCE_DIR = Path("data/screenshots/failures")


class SelectorResolutionError(LookupError):
    """Raised when every strategy for a control fails."""

    def __init__(self, control: str, tried: list[str], evidence_dir: Path | None = None) -> None:
        self.control = control
        self.tried = tried
        self.evidence_dir = evidence_dir
        detail = "; ".join(tried) if tried else "no strategies"
        suffix = f" (evidence: {evidence_dir})" if evidence_dir else ""
        super().__init__(f"Could not resolve control '{control}': {detail}{suffix}")


@dataclass
class Strategy:
    type: str
    value: str | None = None
    role: str | None = None
    name: str | None = None


@dataclass
class ControlSpec:
    name: str
    strategies: list[Strategy] = field(default_factory=list)
    description: str = ""


@dataclass
class SelectorRegistry:
    version: int
    last_verified: str | None
    controls: dict[str, ControlSpec]
    source_path: Path

    @classmethod
    def load(cls, path: str | Path = DEFAULT_SELECTORS_PATH) -> SelectorRegistry:
        config_path = Path(path)
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        controls: dict[str, ControlSpec] = {}
        for name, spec in (raw.get("controls") or {}).items():
            strategies = [
                Strategy(
                    type=str(item.get("type", "css")),
                    value=item.get("value"),
                    role=item.get("role"),
                    name=item.get("name"),
                )
                for item in (spec.get("strategies") or [])
            ]
            controls[name] = ControlSpec(
                name=name,
                strategies=strategies,
                description=str(spec.get("description") or ""),
            )
        return cls(
            version=int(raw.get("version") or 1),
            last_verified=raw.get("last_verified"),
            controls=controls,
            source_path=config_path,
        )

    def get(self, control: str) -> ControlSpec:
        if control not in self.controls:
            raise KeyError(f"Unknown publish control '{control}' in {self.source_path}")
        return self.controls[control]


def _locator_for_strategy(page: Any, strategy: Strategy) -> Any:
    stype = strategy.type.lower()
    if stype == "text":
        if not strategy.value:
            raise ValueError("text strategy requires value")
        return page.get_by_text(strategy.value, exact=False)
    if stype == "css":
        if not strategy.value:
            raise ValueError("css strategy requires value")
        return page.locator(strategy.value)
    if stype == "placeholder":
        if not strategy.value:
            raise ValueError("placeholder strategy requires value")
        return page.get_by_placeholder(strategy.value)
    if stype == "role":
        if not strategy.role:
            raise ValueError("role strategy requires role")
        kwargs: dict[str, Any] = {}
        if strategy.name:
            kwargs["name"] = strategy.name
        return page.get_by_role(strategy.role, **kwargs)
    raise ValueError(f"Unknown strategy type: {strategy.type}")


def _strategy_label(strategy: Strategy) -> str:
    if strategy.type == "role":
        return f"role={strategy.role!r} name={strategy.name!r}"
    return f"{strategy.type}:{strategy.value!r}"


def resolve_locator(
    page: Any,
    registry: SelectorRegistry,
    control: str,
    *,
    timeout_ms: int = 8000,
    state: str = "visible",
) -> Any:
    """Try each strategy until one element reaches the desired state."""
    spec = registry.get(control)
    tried: list[str] = []
    last_error: Exception | None = None

    for strategy in spec.strategies:
        label = _strategy_label(strategy)
        try:
            locator = _locator_for_strategy(page, strategy).first
            locator.wait_for(state=state, timeout=timeout_ms)
            return locator
        except Exception as exc:  # noqa: BLE001 — try next strategy
            tried.append(f"{label} ({exc.__class__.__name__})")
            last_error = exc
            continue

    evidence = dump_failure_evidence(page, control=control, tried=tried)
    raise SelectorResolutionError(control, tried, evidence) from last_error


def dump_failure_evidence(
    page: Any,
    *,
    control: str,
    tried: list[str] | None = None,
    evidence_dir: Path = DEFAULT_EVIDENCE_DIR,
) -> Path:
    """Write screenshot + HTML + tried-strategies note for a failed resolve."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = evidence_dir / f"{control}_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(out / "page.png"), full_page=True)
    except Exception:
        (out / "page.png.error").write_text("screenshot failed\n")
    try:
        (out / "page.html").write_text(page.content(), encoding="utf-8")
    except Exception as exc:
        (out / "page.html.error").write_text(f"{exc}\n")
    note_lines = [
        f"control: {control}",
        f"url: {getattr(page, 'url', '')}",
        f"time: {ts}",
        "tried:",
    ]
    for item in tried or []:
        note_lines.append(f"  - {item}")
    (out / "tried.txt").write_text("\n".join(note_lines) + "\n", encoding="utf-8")
    return out
