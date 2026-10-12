"""Args: add-on folder, FreeMoCap recording folder, output .blend, fps."""

import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import bootstrap  # noqa: E402

addon, recording, out, fps = bootstrap.args()
sys.path.insert(0, addon)
import bpy  # noqa: E402
from ajc27_freemocap_blender_addon.main import ajc27_run_as_main_function  # noqa: E402

ajc27_run_as_main_function(recording_path=recording, blend_file_path=out)
bpy.ops.wm.open_mainfile(filepath=out)
bpy.context.scene.render.fps = int(fps)
bpy.context.scene.render.fps_base = 1.0
bpy.ops.wm.save_mainfile(filepath=out)
bootstrap.result("blend", out)
