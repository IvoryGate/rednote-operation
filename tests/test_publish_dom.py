"""Tests for publish selector registry and multi-strategy resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from src.core.publish_dom import (
    SelectorRegistry,
    SelectorResolutionError,
    dump_failure_evidence,
    resolve_locator,
)


def test_load_default_registry() -> None:
    registry = SelectorRegistry.load()
    assert registry.version >= 1
    assert "publish_trigger" in registry.controls
    assert "title" in registry.controls
    assert registry.controls["title"].strategies


def test_load_custom_registry(tmp_path: Path) -> None:
    path = tmp_path / "sel.yaml"
    path.write_text(
        yaml.dump(
            {
                "version": 2,
                "last_verified": "2099-01-01",
                "controls": {
                    "title": {
                        "strategies": [
                            {"type": "placeholder", "value": "标题"},
                            {"type": "css", "value": "#title"},
                        ]
                    }
                },
            }
        )
    )
    registry = SelectorRegistry.load(path)
    assert registry.version == 2
    assert len(registry.get("title").strategies) == 2


class _FakeLocator:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.first = self

    def wait_for(self, state: str = "visible", timeout: int = 0) -> None:
        if self.fail:
            raise TimeoutError(f"timeout state={state} timeout={timeout}")


class _FakePage:
    def __init__(self) -> None:
        self.url = "https://creator.xiaohongshu.com/publish"
        self._calls: list[str] = []

    def get_by_text(self, value: str, exact: bool = False) -> _FakeLocator:
        self._calls.append(f"text:{value}")
        return _FakeLocator(fail=True)

    def locator(self, value: str) -> _FakeLocator:
        self._calls.append(f"css:{value}")
        # Succeed on second css strategy in fixture below
        return _FakeLocator(fail="#ok" not in value)

    def get_by_placeholder(self, value: str) -> _FakeLocator:
        self._calls.append(f"placeholder:{value}")
        return _FakeLocator(fail=True)

    def get_by_role(self, role: str, **kwargs: object) -> _FakeLocator:
        self._calls.append(f"role:{role}:{kwargs}")
        return _FakeLocator(fail=True)

    def screenshot(self, path: str, full_page: bool = False) -> None:
        Path(path).write_bytes(b"fake")

    def content(self) -> str:
        return "<html>publish form</html>"


def test_resolve_falls_through_strategies(tmp_path: Path) -> None:
    path = tmp_path / "sel.yaml"
    path.write_text(
        yaml.dump(
            {
                "version": 1,
                "controls": {
                    "title": {
                        "strategies": [
                            {"type": "placeholder", "value": "标题"},
                            {"type": "css", "value": "input.bad"},
                            {"type": "css", "value": "input#ok"},
                        ]
                    }
                },
            }
        )
    )
    registry = SelectorRegistry.load(path)
    page = _FakePage()
    loc = resolve_locator(page, registry, "title", timeout_ms=10)
    assert isinstance(loc, _FakeLocator)
    assert any("input#ok" in c for c in page._calls)


def test_resolve_dumps_evidence_on_failure(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "sel.yaml"
    path.write_text(
        yaml.dump(
            {
                "version": 1,
                "controls": {
                    "title": {
                        "strategies": [
                            {"type": "css", "value": "input.missing"},
                        ]
                    }
                },
            }
        )
    )
    evidence_root = tmp_path / "failures"
    monkeypatch.setattr("src.core.publish_dom.DEFAULT_EVIDENCE_DIR", evidence_root)
    registry = SelectorRegistry.load(path)
    page = _FakePage()
    with pytest.raises(SelectorResolutionError) as exc:
        resolve_locator(page, registry, "title", timeout_ms=10)
    assert exc.value.evidence_dir is not None
    assert (exc.value.evidence_dir / "page.html").exists()
    assert (exc.value.evidence_dir / "tried.txt").exists()


def test_dump_failure_evidence_writes_files(tmp_path: Path) -> None:
    page = _FakePage()
    out = dump_failure_evidence(
        page, control="title", tried=["css:'x' (TimeoutError)"], evidence_dir=tmp_path
    )
    assert (out / "page.png").exists()
    assert (out / "page.html").read_text() == "<html>publish form</html>"
    assert "title" in (out / "tried.txt").read_text()
