import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


_ICLOUD_MARKER = "com~apple~CloudDocs"


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
    print("  警告: iCloudへのアップロード確認・evictに失敗しました（手動で確認してください）", file=sys.stderr)


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


def cmd_list(cfg: dict) -> None:
    icloud_dir = Path(cfg["icloud_dir"])
    local_dir = Path(cfg["local_dir"])

    print("=== ロード済み (Local) ===")
    local_projects = sorted(p for p in local_dir.iterdir() if p.is_dir()) if local_dir.exists() else []
    if local_projects:
        for p in local_projects:
            tag = "  [iCloudにバックアップあり]" if (icloud_dir / f"{p.name}.zip").exists() else ""
            print(f"  {p.name}{tag}")
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
            print(f"  {name}{tag}")
    else:
        print("  (なし)")


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
        zf.extractall(dest_path)

    children = list(dest_path.iterdir())
    if len(children) == 1 and children[0].is_dir() and children[0].name == project:
        inner = children[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest_path / item.name))
        inner.rmdir()

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

    tmp_zip = zip_path.with_suffix(".tmp.zip")
    try:
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in src_path.rglob("*"):
                zf.write(file, file.relative_to(src_path))
        tmp_zip.replace(zip_path)
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
