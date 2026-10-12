"""Print the Blender and Python versions and whether MPFB is enabled."""

import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import bootstrap  # noqa: E402

bootstrap.args()
import bpy  # noqa: E402

bootstrap.result("blender", bpy.app.version_string)
bootstrap.result("python", sys.version.split()[0])
bootstrap.result("mpfb", any(name.endswith(".mpfb") for name in bpy.context.preferences.addons.keys()))
