"""control_surface: MIDI control surfaces as an extension of Blender's interface.

bpy is imported only inside register()/unregister(), so the pure modules
(profile, leds, engine) import and test without Blender.
"""


def register():
    from . import blender_glue

    blender_glue.register()


def unregister():
    from . import blender_glue

    blender_glue.unregister()
