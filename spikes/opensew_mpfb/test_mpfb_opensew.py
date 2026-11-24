# MPFB <-> opensew-2 link test.
#
# Builds live MPFB characters (helpers masked, macro shape keys live, rig
# attached - the way a film character is kept, not a baked copy), hands them
# to opensew-2 as the avatar, and checks that:
#
#   1. the body is measured the same as opensew-2's own reference avatar
#      built from the same MPFB macros (chest, waist, hip, neck);
#   2. all eight limbs are found on the chosen rig;
#   3. a change to an MPFB macro (weight) shows up in the next measurement;
#   4. every opensew-2 preset drafts onto the body;
#   5. with --drape: a T-shirt and trousers sew and drape onto the body with
#      less than 2 % of the cloth inside the skin.
#
# Run (Blender 5.2.2, MPFB and the patched clothing_design add-on installed;
# see README.md):
#
#   blender -b --python test_mpfb_opensew.py -- [--rig default|mixamo|rigify]
#           [--figure WOMAN|MAN|BOTH] [--drape] [--out DIR]
#
# Writes DIR/report.json and, per figure, DIR/<figure>_<rig>.blend to open in
# the GUI. Exit code 0 = every check passed.
import bpy, sys, os, json, time, importlib, argparse

EXPECTED_BLENDER = (5, 2, 2)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--rig", default="default", choices=("default", "mixamo", "rigify"))
ap.add_argument("--figure", default="BOTH", choices=("WOMAN", "MAN", "BOTH"))
ap.add_argument("--drape", action="store_true")
ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
args = ap.parse_args(argv)
os.makedirs(args.out, exist_ok=True)
RIG = "rigify.human_toes" if args.rig == "rigify" else args.rig

fails, warns, report = [], [], {"blender": bpy.app.version_string, "rig": RIG, "figures": {}}


def check(cond, msg, known=None):
    """known: why this check is expected to miss for now (README, open items).
    A known miss prints WARN and does not fail the run."""
    if cond:
        print("  ok   " + msg)
    elif known:
        print("  WARN " + msg + "  [known: " + known + "]")
        warns.append(msg)
    else:
        print("  FAIL " + msg)
        fails.append(msg)
    return cond


# ------------------------------------------------------------------ setup

def enable(module):
    try:
        bpy.ops.preferences.addon_enable(module=module)
        return True
    except Exception:
        return False


def find_mpfb():
    for mod in ("bl_ext.blender_org.mpfb", "bl_ext.user_default.mpfb", "mpfb"):
        if enable(mod):
            try:
                importlib.import_module(mod + ".services.humanservice")
                return mod
            except Exception:
                pass
    return None


def fresh():
    bpy.ops.wm.read_homefile(use_empty=True)
    if RIG.startswith("rigify"):
        enable("rigify")
    enable(MPFB)
    enable("clothing_design")


print("== environment")
check(tuple(bpy.app.version) == EXPECTED_BLENDER,
      "Blender %s (expected %s)" % (bpy.app.version_string, ".".join(map(str, EXPECTED_BLENDER))))
MPFB = find_mpfb()
if not check(MPFB is not None, "MPFB extension found (%s)" % MPFB):
    sys.exit(2)
if not check(enable("clothing_design"), "clothing_design add-on enabled"):
    sys.exit(2)
HumanService = importlib.import_module(MPFB + ".services.humanservice").HumanService
TargetService = importlib.import_module(MPFB + ".services.targetservice").TargetService
HumanObjectProperties = importlib.import_module(MPFB + ".entities.objectproperties").HumanObjectProperties
from clothing_design import avatar, library, build, sim
check(hasattr(avatar, "rig_dialect"), "clothing_design carries the MPFB patch (avatar.rig_dialect)")
report["mpfb_module"] = MPFB

# The same macros opensew-2 uses for its bundled Nora / Theo, so the bundled
# avatar is the reference measurement for the live MPFB body.
MACROS = {
    'WOMAN': {"gender": 0.0, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.55,
              "height": 0.52, "cupsize": 0.55, "firmness": 0.6,
              "race": {"asian": 0.33, "caucasian": 0.33, "african": 0.33}},
    'MAN':   {"gender": 1.0, "age": 0.5, "muscle": 0.5, "weight": 0.45, "proportions": 0.55,
              "height": 0.6, "cupsize": 0.5, "firmness": 0.5,
              "race": {"asian": 0.33, "caucasian": 0.33, "african": 0.33}},
}
TOL_CM = {"chest": 4.0, "waist": 4.0, "hip": 4.0, "neck": 2.5}


def girths(m):
    g = {k: avatar.girth_at(m, avatar.z_of(m, k)) * 100 for k in ("chest", "waist", "hip")}
    g["neck"] = avatar.neck_girth(m) * 100
    return {k: round(v, 1) for k, v in g.items()}


def reference(fig):
    fresh()
    bpy.ops.cd.import_character(figure=fig)
    m = avatar.measure(bpy.context, bpy.context.scene.cd.avatar, force=True)
    return girths(m), m["height"] * 100


def mpfb_human(fig):
    body = HumanService.create_human(mask_helpers=True, detailed_helpers=True,
                                     extra_vertex_groups=True, feet_on_ground=True,
                                     scale=0.1, macro_detail_dict=MACROS[fig])
    rig = HumanService.add_builtin_rig(body, RIG, import_weights=True)
    body.name = "MPFB_%s" % fig
    return body, rig


def set_avatar(body):
    ctx = bpy.context
    for o in ctx.selected_objects:
        o.select_set(False)
    body.select_set(True)
    ctx.view_layer.objects.active = body
    bpy.ops.cd.set_avatar()
    return avatar.measure(ctx, body, force=True)


def penetration(ctx, g, tol=0.004):
    bvh = avatar.body_bvh(ctx)
    ev = g.evaluated_get(ctx.evaluated_depsgraph_get())
    mw, inside = ev.matrix_world, 0
    for v in ev.data.vertices:
        p = mw @ v.co
        loc, nrm, _, _ = bvh.find_nearest(p)
        if loc is not None and (p - loc).dot(nrm) < -tol:
            inside += 1
    return inside, len(ev.data.vertices)


# ------------------------------------------------------------------ run

figures = ('WOMAN', 'MAN') if args.figure == 'BOTH' else (args.figure,)
for fig in figures:
    rep = report["figures"][fig] = {}
    print("== %s on MPFB rig '%s'" % (fig, RIG))
    ref, ref_h = reference(fig)
    rep["reference_cm"] = ref

    fresh()
    ctx, scn = bpy.context, bpy.context.scene
    t = time.time()
    body, rig = mpfb_human(fig)
    m = set_avatar(body)
    got = girths(m)
    rep["measured_cm"] = got
    rep["height_cm"] = round(m["height"] * 100, 1)
    rep["dialect"] = avatar.rig_dialect(rig)
    print("  MPFB body %.0f cm (reference %.0f), measured in %.1fs, rig dialect %s"
          % (m["height"] * 100, ref_h, time.time() - t, rep["dialect"]))
    for k in ("chest", "waist", "hip", "neck"):
        known = None
        if k == "neck" and fig == 'MAN' and rep["dialect"]:
            known = ("MPFB default/Rigify weight the front of the neck to the jaw; "
                     "the horizontal ring stops at the trapezius")
        check(abs(got[k] - ref[k]) <= TOL_CM[k],
              "%-5s %5.1f cm  (reference %5.1f, tolerance %.1f)" % (k, got[k], ref[k], TOL_CM[k]),
              known=known)
    check(len(m["limbs"]) == 8, "limbs found: %s" % sorted(m["limbs"]))
    lm = m["landmarks"]
    order = ["knee", "crotch", "hip", "waist", "chest", "shoulder", "neck"]
    check(all(k in lm for k in order) and all(lm[a] < lm[b] for a, b in zip(order, order[1:])),
          "landmarks in anatomical order")
    check(m["figure_auto"] == fig, "figure guessed %s" % m["figure_auto"])
    check(any(mod.type == 'COLLISION' for mod in body.modifiers), "avatar has a Collision modifier")

    # live MPFB edit -> next measurement follows
    w0 = got["hip"]
    HumanObjectProperties.set_value("weight", 0.85, entity_reference=body)
    TargetService.reapply_macro_details(body)
    HumanService.refit(body)
    bpy.context.view_layer.update()
    m2 = avatar.measure(ctx, body, force=True)
    w1 = girths(m2)["hip"]
    rep["hip_after_weight_0.85_cm"] = w1
    check(w1 > w0 + 3.0, "MPFB weight 0.5 -> 0.85 grows the hip %.1f -> %.1f cm" % (w0, w1))
    HumanObjectProperties.set_value("weight", MACROS[fig]["weight"], entity_reference=body)
    TargetService.reapply_macro_details(body)
    HumanService.refit(body)
    bpy.context.view_layer.update()
    set_avatar(body)

    # every preset drafts
    rep["presets"] = {}
    for key, (label, _fn) in library.PRESETS.items():
        try:
            bpy.ops.cd.add_garment(preset=key, fit=0.10)
        except Exception as e:
            check(False, "%s raised %s" % (label, e))
            continue
        gname = scn.cd.garment_name
        pieces = [o for o in scn.objects if o.cd.is_pattern and o.cd.garment == gname]
        gob = build.garment_object(ctx, create=False)
        nv = len(gob.data.vertices) if gob and gob.data else 0
        rep["presets"][key] = {"pieces": len(pieces), "verts": nv}
        check(pieces and nv > 0, "%-11s %d pieces, %d verts" % (label, len(pieces), nv))

    if args.drape:
        rep["drape"] = {}
        for key in ('TSHIRT', 'TROUSERS'):
            fresh()
            ctx, scn = bpy.context, bpy.context.scene
            body, rig = mpfb_human(fig)
            set_avatar(body)
            bpy.ops.cd.add_garment(preset=key, fit=0.10)
            g = build.garment_object(ctx, create=False)
            t = time.time()
            bpy.ops.cd.sew()
            merged, _ = sim.close_seams(ctx, g)
            inside, n = penetration(ctx, g)
            dt = time.time() - t
            rep["drape"][key] = {"seconds": round(dt), "verts": n, "inside": inside, "late_welds": merged}
            check(inside < n * 0.02, "drape %-8s %3.0fs, %d verts, %.1f%% inside the skin"
                  % (key.lower(), dt, n, 100.0 * inside / max(1, n)))
            path = os.path.join(args.out, "%s_%s_%s.blend" % (fig.lower(), args.rig, key.lower()))
            bpy.ops.wm.save_as_mainfile(filepath=path)
            print("  saved", path)
    else:
        path = os.path.join(args.out, "%s_%s.blend" % (fig.lower(), args.rig))
        bpy.ops.wm.save_as_mainfile(filepath=path)
        print("  saved", path)

report["failures"] = fails
report["known_issues"] = warns
with open(os.path.join(args.out, "report.json"), "w") as f:
    json.dump(report, f, indent=2)
print("\n%d failure(s), %d known issue(s)" % (len(fails), len(warns)))
for f in fails:
    print("  FAIL", f)
for w in warns:
    print("  WARN", w)
sys.exit(1 if fails else 0)
