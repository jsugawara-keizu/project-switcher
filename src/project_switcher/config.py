import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "project-switcher" / "config.json"

DEFAULTS = {
    "icloud_dir": str(
        Path.home()
        / "Library"
        / "Mobile Documents"
        / "com~apple~CloudDocs"
        / "Cloud Workspaces"
    ),
    "local_dir": str(Path.home() / "Local Workspaces"),
    "descriptions": {},
    "protected": [],
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    with CONFIG_PATH.open() as f:
        data = json.load(f)
    return {**DEFAULTS, **data}


def save(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"設定を保存しました: {CONFIG_PATH}")


def show() -> None:
    cfg = load()
    print(f"設定ファイル: {CONFIG_PATH}")
    print(f"  icloud_dir : {cfg['icloud_dir']}")
    print(f"  local_dir  : {cfg['local_dir']}")
