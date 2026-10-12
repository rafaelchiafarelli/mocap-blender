"""`mocap-blender` command line: the MVP's Blender steps, one per command."""

import argparse
import sys
from pathlib import Path

from mocap_blender import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mocap-blender", description=__doc__)
    parser.add_argument("--version", action="version", version=f"mocap-blender {__version__}")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("reference", help="the FreeMoCap add-on's scene: <take>/blender/freemocap.blend")
    p.add_argument("take_dir", type=Path)
    p = sub.add_parser("character", help="an MPFB placeholder with a Rigify metarig, from a character JSON")
    p.add_argument("character_json", type=Path)
    p.add_argument("out_blend", type=Path)
    p = sub.add_parser("retarget", help="the take onto the character: <take>/blender/performance.blend")
    p.add_argument("take_dir", type=Path)
    p.add_argument("character_blend", type=Path)
    p = sub.add_parser("shot", help="render a shot recipe on <take>/blender/performance.blend")
    p.add_argument("take_dir", type=Path)
    p.add_argument("recipe_json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    from mocap_blender.blender import BlenderError
    from mocap_blender.character import CharacterError, make_character
    from mocap_blender.performance import retarget_take
    from mocap_blender.reference import reference_scene
    from mocap_blender.shot import ShotError, render_shot

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "reference":
            print(f"wrote {reference_scene(args.take_dir)}")
        elif args.command == "character":
            found = make_character(args.character_json, args.out_blend)
            print(f"wrote {args.out_blend} (rig {found['rig']}, {found['height_m']} m)")
        elif args.command == "retarget":
            report = retarget_take(args.take_dir, args.character_blend)
            print(f"wrote {args.take_dir / 'blender' / 'performance.blend'}: {report['frames']} frames at "
                  f"{report['fps']} fps, scale {report['scale']:.3f}, ground plane {report['ground_plane']}")
        elif args.command == "shot":
            print(f"wrote {render_shot(args.take_dir, args.recipe_json)}")
        else:
            parser.print_help()
    except (BlenderError, CharacterError, ShotError, OSError, ValueError) as e:
        print(f"mocap-blender {args.command}: {e}", file=sys.stderr)
        return 1
    return 0
