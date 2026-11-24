# control_surface — usage

For the person at the controller. What every button does is in
[`../acoes-4mix.md`](../acoes-4mix.md) (Portuguese, numbered, Object/Edit
columns) and in the table of [`../README.md`](../README.md).

## Install or update

From WSL, in the `mocap-blender` repository root:

```bash
B=/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/blender.exe
"$B" --command extension build --source-dir "$(wslpath -w control_surface)" \
     --output-dir 'G:\mocap-studio-downloads\review\<date>'
"$B" --command extension install-file -r user_default -e 'G:\mocap-studio-downloads\review\<date>\control_surface-<version>.zip'
```

Restart Blender after installing. The add-on lives only in the portable
Blender on G: (open it with `G:\mocap-studio-downloads\review\2026-11-20\abrir_blender_5.2.2.bat`).

## Connect

1. Plug the 4-Mix in by USB.
2. In the 3D View press **N**, open the **DJ-Tech** tab, click **Connect**.
   The LEDs play the intro (~1.3 s).
3. The panel shows the status, the decks (`UNKNOWN` until a deck switch or a
   control on that side is used), SHIFT, the tools, `step` and the last
   error.
4. **Disconnect** (or closing Blender) releases the ports and turns the LEDs
   off.

Two Blenders can be connected at once: the one focused last owns the
controller; the other shows "Standby" and does nothing until it is clicked.

## Daily use, in short

- **Top row**: S1/S2 PLAY = Object/Edit Mode; A–D = projection and framing;
  CUE A/B/C = Front/Top/Right views (again: the opposite side); CUE D = camera
  view; the encoder zooms (camera view: dolly); S1 VOL sets `step`
  (1–10 cm) for every platter move; S2 VOL sets Blender's grid (1 mm–10 m),
  the grid that grid snapping lands on.
- **Deck C (left)**: 1–4 move free/X/Y/Z, RE scale, IN rotate, SYNC moves the
  view; the left platter pushes by `step`; the same number again confirms.
  CUP/CUE/PLAY clear (Object) or extrude/inset/bevel (Edit).
- **OUT, any deck, no menu open**: twice deletes the selection (the first press
  arms it and every OUT blinks; 5 s or any other key disarms it).
- **Deck A (left)**: IN opens the Add menu (an added object's settings open
  right after: platter, IN to edit, OUT/SYNC to close); 1 puts the 3D cursor at the mouse;
  2/3/4 choose an axis for the platter to move the cursor (CUP, CUE or PLAY/PAUSE turn it off); SYNC/CUP/CUE/PLAY
  are the Snap menu (alone: the cursor, with SHIFT: the selection). CUP twice
  (the second while CUP is lit, 3 s) = vertex pick: the platter walks the active object's
  vertices; CUP again keeps the cursor there.
- **Deck B (right)**: IN opens the Properties menu; the right platter moves
  the rows or the value; IN enters/keeps, OUT back/undo, SYNC closes.
- **VINYL left (A or C)**: snapping off → grid (lit) → geometry (blinking).
  **VINYL right (B or D)**: Edit Mode vertex → edge → face; Object Mode:
  Orbit Around Selection.

## The 4-Mix window

It opens by itself with the Add or the Properties menu and closes with them.
Drag it once where you want it: it reopens there. Click a row = IN; the
fields work with the mouse; ← = OUT; ✕ = SYNC. A click anywhere outside it
closes the menus like SYNC; moving the mouse away or Alt+Tab does not.

## Debugging a problem

1. DJ-Tech panel → click **Debug log: off**; it becomes **Debug log: ON (click to stop)**.
2. Reproduce the problem; note the time and what you pressed.
3. Click it again to stop.
4. The log is `%TEMP%\control_surface_midi.log`
   (`C:\Users\<you>\AppData\Local\Temp\`). Each line:
   `<ms since Connect>  IN|OUT|STATE  <b0 b1 b2>  <control event>`; STATE
   lines show `owner`, `sync`, `scale`, `rotate`, `cage`, `grab` and the
   layers whenever they change. Send the file (or the part around the
   problem) with what you expected.
5. The last error also shows at the bottom of the DJ-Tech panel; Blender's
   console (Window → Toggle System Console) shows Python errors.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "not found" on Connect | the 4-Mix is not plugged in, or its port name changed (`port_name_contains` in the profile) |
| "port in use" | another program holds the port (VirtualDJ, a probe script) on the old Windows MIDI stack |
| Nothing happens, panel says Standby | another Blender owns the controller: click this Blender's window |
| A knob does nothing after Connect | centre-tap knobs (FILTER, EQ) wait until they pass their centre |
| A fader's value is wrong at first | faders report nothing until moved: move it once |
| The deck shows UNKNOWN | press the deck switch or any control on that side |
| The 4-Mix window does not open | the console shows "control_surface: 4-Mix window: …"; the menu is then drawn on the viewport |
