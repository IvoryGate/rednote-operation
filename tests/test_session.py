# mypy: ignore-errors
from pathlib import Path

from src.core.session import SessionManager


def test_session_manager(tmp_path: Path) -> None:
    mgr = SessionManager("test_account")
    mgr.state_dir = tmp_path / "test_account"
    mgr.state_file = mgr.state_dir / "state.json"

    assert mgr.has_session() is False
    assert mgr.load_state() is None

    state = {"cookies": [{"name": "session", "value": "abc123"}]}
    mgr.save_state(state)
    assert mgr.has_session() is True
    assert mgr.load_state() == state

    mgr.clear_session()
    assert mgr.has_session() is False


def test_session_get_user_data_dir(tmp_path: Path) -> None:
    mgr = SessionManager("test_account")
    mgr.state_dir = tmp_path / "test_account"

    user_dir = mgr.get_user_data_dir()
    assert Path(user_dir).exists()


def test_session_multiple_accounts(tmp_path: Path) -> None:
    a1 = SessionManager("alice")
    a1.state_dir = tmp_path / "alice"
    a1.state_file = a1.state_dir / "state.json"
    a2 = SessionManager("bob")
    a2.state_dir = tmp_path / "bob"
    a2.state_file = a2.state_dir / "state.json"

    a1.save_state({"user": "alice"})
    a2.save_state({"user": "bob"})

    assert a1.load_state() == {"user": "alice"}
    assert a2.load_state() == {"user": "bob"}
    assert a1.load_state() != a2.load_state()


def test_session_empty_state_file(tmp_path: Path) -> None:
    mgr = SessionManager("empty_test")
    mgr.state_dir = tmp_path / "empty_test"
    mgr.state_file = mgr.state_dir / "state.json"
    mgr.state_dir.mkdir(parents=True, exist_ok=True)
    mgr.state_file.write_text("{}")

    assert mgr.load_state() == {}
    assert mgr.has_session() is True
