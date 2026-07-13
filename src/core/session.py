import json
from pathlib import Path

from src.core.config import config


class SessionManager:
    def __init__(self, account_name: str = "main") -> None:
        self.account_name = account_name
        self.state_dir = Path(config.browser.user_data_dir) / account_name
        self.state_file = self.state_dir / "state.json"

    def ensure_dir(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: dict) -> None:
        self.ensure_dir()
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self) -> dict | None:
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return None

    def has_session(self) -> bool:
        return self.state_file.exists()

    def clear_session(self) -> None:
        if self.state_file.exists():
            self.state_file.unlink()

    def get_user_data_dir(self) -> str:
        self.ensure_dir()
        return str(self.state_dir)


def check_login_status(page: object) -> bool:
    """Check if currently logged in by visiting the creator page."""
    # TODO: implement actual login status check
    return False
