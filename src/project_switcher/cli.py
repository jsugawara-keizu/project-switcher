import argparse
import sys

import argcomplete

from . import config as cfg_module
from .commands import available_to_load, available_to_unload, cmd_desc, cmd_list, cmd_load, cmd_protect, cmd_unload


def _load_completer(prefix, parsed_args, **kwargs):
    try:
        c = cfg_module.load()
        return [p for p in available_to_load(c) if p.startswith(prefix)]
    except Exception:
        return []


def _unload_completer(prefix, parsed_args, **kwargs):
    try:
        c = cfg_module.load()
        return [p for p in available_to_unload(c) if p.startswith(prefix)]
    except Exception:
        return []


def _all_projects_completer(prefix, parsed_args, **kwargs):
    try:
        c = cfg_module.load()
        all_projects = set(available_to_load(c)) | set(available_to_unload(c))
        return [p for p in sorted(all_projects) if p.startswith(prefix)]
    except Exception:
        return []


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pswitch",
        description="プロジェクトをiCloudとローカルワークスペース間でロード/アンロードする",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    sub.add_parser("list", help="ロード済み・アンロード済みプロジェクトの一覧表示")

    p_load = sub.add_parser("load", help="iCloudからローカルへプロジェクトを展開")
    p_load.add_argument("projects", nargs="+", metavar="project", help="プロジェクト名（複数指定可）").completer = _load_completer

    p_unload = sub.add_parser("unload", help="ローカルからiCloudへZip圧縮して移動")
    p_unload.add_argument("projects", nargs="+", metavar="project", help="プロジェクト名（複数指定可）").completer = _unload_completer

    p_desc = sub.add_parser("desc", help="プロジェクトの説明を登録・表示・削除")
    p_desc.add_argument("project", metavar="project", help="プロジェクト名").completer = _all_projects_completer
    p_desc_group = p_desc.add_mutually_exclusive_group()
    p_desc_group.add_argument("description", nargs="?", metavar="description", help="登録する説明文（省略で表示）")
    p_desc_group.add_argument("--delete", action="store_true", help="説明を削除")

    p_protect = sub.add_parser("protect", help="プロジェクトのアンロード禁止を設定・解除")
    p_protect.add_argument("project", metavar="project", help="プロジェクト名").completer = _all_projects_completer
    p_protect.add_argument("--remove", action="store_true", help="アンロード禁止を解除")

    p_config = sub.add_parser("config", help="設定の表示・変更")
    p_config.add_argument("--icloud-dir", metavar="PATH", help="iCloud側のZip保存ディレクトリ")
    p_config.add_argument("--local-dir", metavar="PATH", help="ローカルワークスペースディレクトリ")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "config":
        if args.icloud_dir or args.local_dir:
            c = cfg_module.load()
            if args.icloud_dir:
                c["icloud_dir"] = args.icloud_dir
            if args.local_dir:
                c["local_dir"] = args.local_dir
            cfg_module.save(c)
        cfg_module.show()
        return

    c = cfg_module.load()

    if args.command == "list":
        cmd_list(c)
    elif args.command == "load":
        cmd_load(args.projects, c)
    elif args.command == "unload":
        cmd_unload(args.projects, c)
    elif args.command == "desc":
        description = "" if args.delete else args.description
        cmd_desc(args.project, description, c)
    elif args.command == "protect":
        cmd_protect(args.project, args.remove, c)
