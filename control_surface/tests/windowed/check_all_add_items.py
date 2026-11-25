"""Validation round, part 2 (task 53): every item of deck A's Add menu, through the real path,
in Object Mode and in mesh Edit Mode (a windowed Blender, a Session with fake MIDI ports).

For each item (items ending in "…" open a dialog or a file browser and are skipped):
1. reset the scene (the Cube, Object Mode; for Edit Mode, the Cube in Edit Mode, all selected);
2. IN on deck A opens the Add menu (the 4-Mix window opens), each level is entered the way
   the platter + IN would (index set, then IN), and IN on the item adds it — the 4-Mix window
   closes at that moment, where 0.1.54 crashed with the Circle;
3. if the settings open: check they show the values the object was built with (a stale
   group once showed the last add's), then change the first number field (the object is rebuilt);
4. OUT on deck A closes; record the result, the settings, the error.
Progress goes to all_add_items.progress.json after every item, so a crash shows where.
Result: all_add_items.json and all_add_items.md (Portuguese, for Rafael).

Run from WSL (a few minutes; do not use the PC meanwhile):
    CHECK_TIMEOUT=900 ./run.sh check_all_add_items.py
"""
import ctypes
import json
import os
import sys
from ctypes import wintypes

import bpy

root, out = sys.argv[sys.argv.index("--") + 1:][:2]
sys.path.insert(0, root)
import control_surface  # noqa: E402

control_surface.register()
from control_surface import add_config, add_menu, blender_glue as g, menu_window, oswindow, props_menu  # noqa: E402

u = ctypes.windll.user32
PROFILE = json.load(open(os.path.join(root, "control_surface", "devices", "dj_tech_4mix.json")))["controls"]
TICK = 0.25
st = {"results": []}


class FakeIn:
    def close(self): pass


class FakeOut:
    def send(self, *m): pass
    def close(self): pass


def send(cid):
    c = PROFILE[cid]
    st["s"].queue.put(tuple(c["press"]))
    st["s"].queue.put(tuple(c["release"]))


def leaves(items, path=(), names=()):
    for i, it in enumerate(items):
        if "items" in it:
            yield from leaves(it["items"], path + (i,), names + (it["text"],))
        else:
            yield path + (i,), names + (it["text"],), it


def skip(it):
    t = it["text"].rstrip()
    return t.endswith("…") or t.endswith("...") or "import" in it["op"] or "file" in it["op"]


def reset(mode):
    add_config.end()
    add_menu.close()
    props_menu.close()
    if bpy.context.mode != "OBJECT":
        g.run_operator("object.mode_set", {"mode": "OBJECT"})
    for o in list(bpy.data.objects):
        if o.name not in st["keep"]:
            bpy.data.objects.remove(o)
    cube = bpy.data.objects["Cube"]
    for o in bpy.data.objects:
        o.select_set(o == cube)
    bpy.context.view_layer.objects.active = cube
    bpy.context.scene.cursor.location = (0, 0, 0)
    if mode == "EDIT_MESH":
        g.run_operator("object.mode_set", {"mode": "EDIT"})
        g.run_operator("mesh.select_all", {"action": "SELECT"})
    st["s"].engine.last_error = ""


def bump_first_number():
    grp = add_config.group()
    for n in add_config._session["names"]:
        p = grp.bl_rna.properties[n]
        if p.type in ("INT", "FLOAT") and not getattr(p, "is_array", False):
            v = getattr(grp, n)
            nv = v + 1 if p.type == "INT" else v * 1.5 + 0.1
            setattr(grp, n, min(max(nv, p.hard_min), p.hard_max))
            return f"{n}: {v:.3g} -> {getattr(grp, n):.3g}"
    return None


def run_item(mode, path, names, it):
    reset(mode)
    yield TICK
    rec = {"mode": mode, "item": " › ".join(names), "op": it["op"], "props": it["props"]}
    before = len(bpy.data.objects)
    send("IN L/A")                                  # open the Add menu
    yield TICK
    rec["window"] = menu_window.is_open()
    for depth, idx in enumerate(path):
        if not add_menu._stack:
            rec["result"] = "menu closed early"
            rec["error"] = f"depth {depth}; settings {add_config.active()}; props {props_menu.is_open()}; " \
                           f"last_error {st['s'].engine.last_error!r}"
            break
        add_menu._stack[-1]["index"] = idx          # what the platter does
        send("IN L/A")                              # enter / add
        yield TICK + (0.3 if depth == len(path) - 1 else 0)
    else:
        rec["settings"] = add_config.active()
        rec["title"] = add_config._session["title"] if add_config.active() else None
        rec["objects_added"] = len(bpy.data.objects) - before
        rec["error"] = st["s"].engine.last_error
        if add_config.active():
            grp = add_config.group()
            reg = add_config._registered(add_config._session["pointer"]).properties
            rec["settings_match"] = all(add_config._value(getattr(grp, n)) == add_config._value(getattr(reg, n))
                                        for n in add_config._session["names"])
            if not rec["settings_match"]:
                rec["error"] = "the settings show other values than the object was built with"
            rec["changed"] = bump_first_number()
            yield TICK + 0.2
            rec["error_after_change"] = st["s"].engine.last_error
            rec["still_open"] = add_config.active()
            send("OUT L/A")                         # close (short press)
            yield TICK
            rec["closed"] = not add_config.active()
        err = rec.get("error") or rec.get("error_after_change")
        rec["result"] = "error" if err else ("ok" if rec["settings"] else "ok (no settings)")
    st["results"].append(rec)
    json.dump(st["results"], open(os.path.join(out, "all_add_items.progress.json"), "w"), default=str)


def safe(mode, path, names, it):
    try:
        yield from run_item(mode, path, names, it)
    except Exception:
        import traceback
        st["results"].append({"mode": mode, "item": " › ".join(names), "op": it["op"], "result": "error",
                              "error": "check: " + traceback.format_exc()[-500:]})


def all_steps():
    for mode in ("OBJECT", "EDIT_MESH"):
        reset(mode)
        yield TICK
        tree = add_menu.read_menu(add_menu.ROOT_MENUS[mode])
        for path, names, it in leaves(tree):
            if skip(it):
                st["results"].append({"mode": mode, "item": " › ".join(names), "op": it["op"], "result": "skipped (dialog)"})
                continue
            yield from safe(mode, path, names, it)


def report():
    rows = st["results"]
    pt = {"ok": "OK", "ok (no settings)": "OK (sem configuração)", "error": "erro",
          "skipped (dialog)": "pulado (abre diálogo)", "menu closed early": "menu fechou antes"}
    counts = {}
    for r in rows:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
    lines = ["# Rodada de validação — todos os itens do menu Add (deck A)", "",
             f"{len(rows)} itens: " + ", ".join(f"{v} {pt.get(k, k)}" for k, v in counts.items()), "",
             "| Modo | Item | Operador | Resultado | Configuração | Valor mudado | Erro |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        err = (r.get("error") or r.get("error_after_change") or "").replace("|", "/")
        lines.append(f"| {r['mode']} | {r['item']} | {r['op']} | {pt.get(r['result'], r['result'])} | "
                     f"{r.get('title') or '—'} | {r.get('changed') or '—'} | {err} |")
    open(os.path.join(out, "all_add_items.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(rows, open(os.path.join(out, "all_add_items.json"), "w"), default=str)


def start():
    st["main"] = next(iter(oswindow.process_windows()))
    u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0); oswindow.focus(st["main"])
    u.keybd_event(0x1B, 0, 0, 0); u.keybd_event(0x1B, 0, 2, 0)  # the splash
    pt = wintypes.POINT(0, 0); u.ClientToScreen(st["main"], ctypes.byref(pt))
    win = bpy.context.window_manager.windows[0]
    u.SetCursorPos(pt.x + win.width // 3, pt.y + win.height // 2)
    st["keep"] = {o.name for o in bpy.data.objects}
    st["s"] = g.connect(midi_in=FakeIn(), midi_out=FakeOut(), intro=False)
    st["gen"] = all_steps()


def run():
    try:
        if "gen" not in st:
            start()
            return 0.5
        return next(st["gen"])
    except StopIteration:
        report()
        reset("OBJECT")
        g.disconnect()
        bpy.ops.wm.quit_blender()
        return None
    except Exception:
        import traceback
        st["results"].append({"mode": "?", "item": "?", "op": "?", "result": "error", "error": traceback.format_exc()[-800:]})
        return TICK


bpy.app.timers.register(run, first_interval=2.0, persistent=True)
