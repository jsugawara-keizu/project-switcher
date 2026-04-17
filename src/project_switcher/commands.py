import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path


_ICLOUD_MARKER = "com~apple~CloudDocs"
_BAR_WIDTH = 30


def _progress(label: str, current: int, total: int) -> None:
    pct = current / total if total else 1.0
    filled = int(_BAR_WIDTH * pct)
    bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
    print(f"\r  {label} [{bar}] {pct:5.1%} ({current}/{total})", end="", flush=True)


def _progress_done(label: str, total: int) -> None:
    bar = "█" * _BAR_WIDTH
    print(f"\r  {label} [{bar}] 100.0% ({total}/{total})")


def _is_icloud(path: Path) -> bool:
    return _ICLOUD_MARKER in str(path)


def _icloud_placeholder(p: Path) -> Path:
    return p.parent / f".{p.name}.icloud"


def _ensure_downloaded(zip_path: Path) -> None:
    if not _is_icloud(zip_path):
        return
    placeholder = _icloud_placeholder(zip_path)
    if not placeholder.exists():
        return
    print("  iCloudからダウンロード中...", end="", flush=True)
    try:
        subprocess.run(["brctl", "download", str(zip_path)], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    for _ in range(30):
        if not placeholder.exists():
            break
        time.sleep(2)
        print(".", end="", flush=True)
    print()
    if placeholder.exists():
        print("警告: iCloudダウンロードが完了しませんでした", file=sys.stderr)


def _evict_after_sync(zip_path: Path, timeout: int = 60) -> None:
    if not _is_icloud(zip_path) or not zip_path.exists():
        return

    print("  iCloudへのアップロード完了を待機中...", end="", flush=True)
    waited = 0
    # brctl status でアップロード完了を確認（ファイルに .icloud プレースホルダがない = アップロード済み）
    # iCloud管理フォルダへの書き込み後、少し待ってからevictを試みる
    while waited < timeout:
        try:
            result = subprocess.run(
                ["brctl", "log", "-w", "0"],
                capture_output=True, text=True, timeout=3
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # ファイルがまだローカルに存在し、.icloud プレースホルダが存在しない = アップロード完了
        if zip_path.exists() and not _icloud_placeholder(zip_path).exists():
            try:
                subprocess.run(["brctl", "evict", str(zip_path)], check=True, capture_output=True)
                print(" 削除済み")
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                break

        time.sleep(2)
        waited += 2
        print(".", end="", flush=True)

    print()
    # evict失敗でもアンロード自体は完了しているので警告のみ
    print("  iCloudへのアップロードはバックグラウンドで継続されます", file=sys.stderr)


def available_to_load(cfg: dict) -> list[str]:
    icloud_dir = Path(cfg["icloud_dir"])
    local_dir = Path(cfg["local_dir"])
    if not icloud_dir.exists():
        return []
    names: set[str] = set()
    for z in icloud_dir.iterdir():
        if z.suffix == ".zip":
            names.add(z.stem)
        # iCloud未ダウンロードのプレースホルダ: .foo.zip.icloud → stem=".foo.zip" → [1:][:-4]
        elif z.name.endswith(".zip.icloud") and z.name.startswith("."):
            names.add(z.name[1:-len(".zip.icloud")])
    return sorted(n for n in names if not (local_dir / n).is_dir())


def available_to_unload(cfg: dict) -> list[str]:
    local_dir = Path(cfg["local_dir"])
    if not local_dir.exists():
        return []
    return sorted(p.name for p in local_dir.iterdir() if p.is_dir())


def _fmt_desc(name: str, descriptions: dict) -> str:
    desc = descriptions.get(name, "")
    return f"  # {desc}" if desc else ""


def cmd_list(cfg: dict) -> None:
    icloud_dir = Path(cfg["icloud_dir"])
    local_dir = Path(cfg["local_dir"])
    descriptions = cfg.get("descriptions", {})

    print("=== ロード済み (Local) ===")
    local_projects = sorted(p for p in local_dir.iterdir() if p.is_dir()) if local_dir.exists() else []
    if local_projects:
        for p in local_projects:
            tag = "  [iCloudにバックアップあり]" if (icloud_dir / f"{p.name}.zip").exists() else ""
            print(f"  {p.name}{tag}{_fmt_desc(p.name, descriptions)}")
    else:
        print("  (なし)")

    print()
    print("=== アンロード済み (iCloud) ===")
    icloud_zips = (
        sorted(z for z in icloud_dir.iterdir() if z.suffix == ".zip")
        if icloud_dir.exists()
        else []
    )
    if icloud_zips:
        for z in icloud_zips:
            name = z.stem
            tag = "  ※ローカルにも存在" if (local_dir / name).is_dir() else ""
            print(f"  {name}{tag}{_fmt_desc(name, descriptions)}")
    else:
        print("  (なし)")


def cmd_desc(project: str, description: str | None, cfg: dict) -> None:
    from . import config as cfg_module
    descriptions = cfg.get("descriptions", {})

    if description is None:
        # 説明を表示
        desc = descriptions.get(project, "")
        if desc:
            print(f"{project}: {desc}")
        else:
            print(f"{project}: (説明なし)")
        return

    if description == "":
        # 説明を削除
        descriptions.pop(project, None)
        print(f"{project} の説明を削除しました")
    else:
        descriptions[project] = description
        print(f"{project}: {description}")

    cfg["descriptions"] = descriptions
    cfg_module.save(cfg)


def _load_one(project: str, icloud_dir: Path, local_dir: Path) -> bool:
    zip_path = icloud_dir / f"{project}.zip"
    dest_path = local_dir / project

    if not zip_path.exists() and not _icloud_placeholder(zip_path).exists():
        print(f"Error: Zipファイルが見つかりません: {zip_path}", file=sys.stderr)
        return False

    if dest_path.exists():
        print(f"Error: ローカルに既に展開済みです: {dest_path}", file=sys.stderr)
        return False

    print(f"ロード中: {project}")
    print(f"  展開先: {dest_path}")

    _ensure_downloaded(zip_path)

    dest_path.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        total = len(members)
        for i, member in enumerate(members, 1):
            extracted = dest_path / member.filename
            zf.extract(member, dest_path)
            perm = (member.external_attr >> 16) & 0xFFFF
            if perm:
                os.chmod(extracted, perm)
            _progress("展開", i, total)
    _progress_done("展開", total)

    children = list(dest_path.iterdir())
    if len(children) == 1 and children[0].is_dir() and children[0].name == project:
        inner = children[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest_path / item.name))
        inner.rmdir()

    zip_path.unlink(missing_ok=True)
    print(f"完了: {project} をロードしました")
    return True


def cmd_load(projects: list[str], cfg: dict) -> None:
    icloud_dir = Path(cfg["icloud_dir"])
    local_dir = Path(cfg["local_dir"])
    errors = [p for p in projects if not _load_one(p, icloud_dir, local_dir)]
    if errors:
        sys.exit(1)


def _unload_one(project: str, icloud_dir: Path, local_dir: Path) -> bool:
    src_path = local_dir / project
    zip_path = icloud_dir / f"{project}.zip"

    if not src_path.is_dir():
        print(f"Error: ローカルにプロジェクトが見つかりません: {src_path}", file=sys.stderr)
        return False

    print(f"アンロード中: {project}")
    print(f"  圧縮先: {zip_path}")

    icloud_dir.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip", prefix="pswitch-")
    tmp_zip = Path(tmp_path)
    try:
        files = [f for f in src_path.rglob("*") if f.is_file()]
        total = len(files)
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, file in enumerate(files, 1):
                info = zipfile.ZipInfo.from_file(file, file.relative_to(src_path))
                info.external_attr = (file.stat().st_mode & 0xFFFF) << 16
                with file.open("rb") as f:
                    zf.writestr(info, f.read(), zipfile.ZIP_DEFLATED)
                _progress("圧縮", i, total)
        os.close(tmp_fd)
        _progress_done("圧縮", total)
        shutil.move(str(tmp_zip), str(zip_path))
    except Exception:
        tmp_zip.unlink(missing_ok=True)
        raise

    shutil.rmtree(src_path)

    _evict_after_sync(zip_path)
    print(f"完了: {project} をアンロードしました")
    return True


def cmd_unload(projects: list[str], cfg: dict) -> None:
    icloud_dir = Path(cfg["icloud_dir"])
    local_dir = Path(cfg["local_dir"])
    errors = [p for p in projects if not _unload_one(p, icloud_dir, local_dir)]
    if errors:
        sys.exit(1)
