import argparse
import sys

import argcomplete

from . import config as cfg_module
from .commands import available_to_load, available_to_unload, cmd_list, cmd_load, cmd_unload


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
