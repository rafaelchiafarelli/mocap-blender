"""Retarget FreeMoCap (MediaPipe) landmarks onto a Rigify human metarig. Plain numpy: runs in and out of Blender.

**Normalise the take** (`normalise`): mm to m, gaps filled, hips' median at the origin, the actor facing
-Y with their left towards +X, the lowest foot point at z = 0. Up is +Z when the calibration set a
ground plane, otherwise the median hips-to-shoulders direction.

**Per bone, a frame from two vectors** between named joints that both skeletons have (`BONES`): the
primary vector, then a secondary that fixes the twist around it (with a fallback when the two are
nearly parallel, as in a straight arm). The bone's world rotation is the one that takes its rest
frame onto the actor's frame: R = F_actor @ F_rest.T @ R_rest. It doesn't depend on either rig's rest
pose or bone roll.

**Root:** the hips bone goes to the actor's hips, scaled by the ratio of leg lengths
(character / actor). Every other bone stays attached to its parent. Then the whole body drops (or
rises) so that the lower ankle each frame (2nd percentile over the take) is at its rest height: feet
on the floor, not hovering.

**Feet stay flat** (`FLAT`): they follow the actor's heading but not its pitch, because MediaPipe's toe
landmark is noisy and often low (below the floor), which tipped the feet toes-down. Heel-toe roll is lost.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

BODY = {"nose": 0, "ear.L": 7, "ear.R": 8, "sho.L": 11, "sho.R": 12, "elb.L": 13, "elb.R": 14,
        "wri.L": 15, "wri.R": 16, "hip.L": 23, "hip.R": 24, "knee.L": 25, "knee.R": 26,
        "ank.L": 27, "ank.R": 28, "heel.L": 29, "heel.R": 30, "toe.L": 31, "toe.R": 32}
FINGERS = {"thumb": 1, "index": 5, "middle": 9, "ring": 13, "pinky": 17}  # MediaPipe hand: 4 joints each
POSE_HAND = {"L": {"pinky": 17, "index": 19, "thumb": 21}, "R": {"pinky": 18, "index": 20, "thumb": 22}}
FOOT_JOINTS = ("ank.L", "ank.R", "heel.L", "heel.R", "toe.L", "toe.R")
CONTACT_PERCENTILE = 2
EPS = 1e-6
PARALLEL = 0.05  # |sin| between primary and secondary below this: use the fallback secondary


def _side_bones(s: str) -> dict[str, tuple]:
    bones = {
        f"shoulder.{s}": (("shoulders", f"sho.{s}"), ("hips", "shoulders"), None),
        f"upper_arm.{s}": ((f"sho.{s}", f"elb.{s}"), (f"elb.{s}", f"wri.{s}"), ("hips", "shoulders")),
        f"forearm.{s}": ((f"elb.{s}", f"wri.{s}"), (f"index1.{s}", f"pinky1.{s}"), (f"sho.{s}", f"elb.{s}")),
        f"hand.{s}": ((f"wri.{s}", f"middle1.{s}"), (f"index1.{s}", f"pinky1.{s}"), None),
        f"thigh.{s}": ((f"hip.{s}", f"knee.{s}"), (f"knee.{s}", f"ank.{s}"), ("hip.R", "hip.L")),
        f"shin.{s}": ((f"knee.{s}", f"ank.{s}"), (f"ank.{s}", f"toe.{s}"), ("hip.R", "hip.L")),
        f"foot.{s}": ((f"ank.{s}", f"toe.{s}"), (f"knee.{s}", f"ank.{s}"), None),
    }
    for finger in ("index", "middle", "ring", "pinky"):
        for k in (1, 2, 3):
            bones[f"f_{finger}.0{k}.{s}"] = ((f"{finger}{k}.{s}", f"{finger}{k + 1}.{s}"),
                                              (f"index1.{s}", f"pinky1.{s}"), None)
    for k in (1, 2, 3):
        bones[f"thumb.0{k}.{s}"] = ((f"thumb{k}.{s}", f"thumb{k + 1}.{s}"), (f"wri.{s}", f"middle1.{s}"), None)
    return bones


# bone: (primary (from, to), secondary (from, to), fallback secondary or None)
BONES: dict[str, tuple] = {
    "spine": (("hips", "shoulders"), ("hip.R", "hip.L"), None),
    "spine.001": (("hips", "shoulders"), ("hip.R", "hip.L"), None),
    "spine.002": (("hips", "shoulders"), ("sho.R", "sho.L"), None),
    "spine.003": (("hips", "shoulders"), ("sho.R", "sho.L"), None),
    "spine.004": (("shoulders", "ears"), ("sho.R", "sho.L"), None),
    "spine.005": (("shoulders", "ears"), ("sho.R", "sho.L"), None),
    "spine.006": (("ear.R", "ear.L"), ("ears", "nose"), None),
    **_side_bones("L"), **_side_bones("R"),
}
ROOT = "spine"
FLAT = {"foot.L", "foot.R"}
UP = np.array([0.0, 0.0, 1.0])


def target_joints(heads: dict[str, np.ndarray], tails: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """The named joints on a Rigify human metarig at rest, from bone heads and tails (armature space)."""
    j = {"hips": heads["spine"], "nose": heads["nose.002"]}
    for s in ("L", "R"):
        j |= {f"sho.{s}": heads[f"upper_arm.{s}"], f"elb.{s}": heads[f"forearm.{s}"],
              f"wri.{s}": heads[f"hand.{s}"], f"hip.{s}": heads[f"thigh.{s}"], f"knee.{s}": heads[f"shin.{s}"],
              f"ank.{s}": heads[f"foot.{s}"], f"toe.{s}": tails[f"toe.{s}"], f"ear.{s}": heads[f"ear.{s}"]}
        for finger in ("thumb", "index", "middle", "ring", "pinky"):
            bone = "thumb" if finger == "thumb" else f"f_{finger}"
            for k in (1, 2, 3):
                j[f"{finger}{k}.{s}"] = heads[f"{bone}.0{k}.{s}"]
            j[f"{finger}4.{s}"] = tails[f"{bone}.03.{s}"]
    return _derived(j)


def source_joints(body: np.ndarray, left_hand: np.ndarray, right_hand: np.ndarray) -> dict[str, np.ndarray]:
    """The named joints from FreeMoCap's MediaPipe 3D (frames x points x 3)."""
    j = {name: body[:, i] for name, i in BODY.items()}
    for s, hand in (("L", left_hand), ("R", right_hand)):
        for finger, first in FINGERS.items():
            for k in range(4):
                j[f"{finger}{k + 1}.{s}"] = hand[:, first + k].copy()
        # Frames without hand landmarks (one camera, or a hand FreeMoCap lost): MediaPipe Pose's own hand
        # points orient the hand. They sit further out than the knuckles, which only the directions use.
        pose = {f: body[:, i] for f, i in POSE_HAND[s].items()}
        pose["middle"] = (pose["index"] + pose["pinky"]) / 2
        for finger in ("index", "pinky", "middle"):
            joint = j[f"{finger}1.{s}"]
            lost = np.isnan(joint).any(axis=-1)
            joint[lost] = pose[finger][lost]
    return _derived(j)


def _derived(j: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    j = dict(j)
    j["shoulders"] = (j["sho.L"] + j["sho.R"]) / 2
    j["ears"] = (j["ear.L"] + j["ear.R"]) / 2
    if "hips" not in j:
        j["hips"] = (j["hip.L"] + j["hip.R"]) / 2
    return j


def fill_gaps(points: np.ndarray) -> tuple[np.ndarray, int]:
    """Linear interpolation over time of every NaN sample (frames x points x 3); a point never seen stays NaN."""
    out = points.astype(np.float64)
    filled = 0
    t = np.arange(out.shape[0])
    for p in range(out.shape[1]):
        bad = np.isnan(out[:, p, 0])
        if bad.any() and not bad.all():
            for axis in range(3):
                out[bad, p, axis] = np.interp(t[bad], t[~bad], out[~bad, p, axis])
            filled += int(bad.sum())
    return out, filled


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), EPS)


@dataclass
class Normalised:
    joints: dict[str, np.ndarray]
    """Joint name -> frames x 3, metres, normalised world."""
    filled: int
    """Samples filled by interpolation."""
    rotation: np.ndarray = field(repr=False)
    origin_mm: np.ndarray = field(repr=False)


def normalise(body: np.ndarray, left_hand: np.ndarray, right_hand: np.ndarray, *,
              ground_plane: bool) -> Normalised:
    filled = 0
    parts = []
    for part in (body, left_hand, right_hand):
        part, n = fill_gaps(part)
        parts.append(part)
        filled += n
    raw = source_joints(*parts)
    up = np.array([0.0, 0.0, 1.0]) if ground_plane else _unit(np.nanmedian(raw["shoulders"] - raw["hips"], axis=0))
    lateral = np.nanmedian(raw["hip.L"] - raw["hip.R"], axis=0)
    lateral = _unit(lateral - np.dot(lateral, up) * up)
    rotation = np.stack([lateral, np.cross(up, lateral), up])  # rows: new X (actor's left), Y (actor's back), Z
    origin = np.nanmedian(raw["hips"], axis=0)
    joints = {k: (v - origin) @ rotation.T / 1000.0 for k, v in raw.items()}
    floor = np.nanpercentile(np.concatenate([joints[k][:, 2] for k in FOOT_JOINTS]), 1)
    hips_xy = np.nanmedian(joints["hips"][:, :2], axis=0)
    for v in joints.values():
        v[:, 2] -= floor
        v[:, :2] -= hips_xy
    return Normalised(joints=joints, filled=filled, rotation=rotation, origin_mm=origin)


def frame(primary: np.ndarray, secondary: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    """Orthonormal frames (... x 3 x 3, columns x, y, z): x along primary, y towards secondary."""
    x = _unit(primary)
    s = secondary
    if fallback is not None:
        sin = np.linalg.norm(np.cross(x, _unit(secondary)), axis=-1, keepdims=True)
        s = np.where(sin < PARALLEL, fallback, secondary)
    z = _unit(np.cross(x, s))
    y = np.cross(z, x)
    return np.stack([x, y, z], axis=-1)


def bone_frame(joints: dict[str, np.ndarray], spec: tuple, flat: bool = False) -> np.ndarray:
    (a, b), (c, d), fb = spec
    primary = joints[b] - joints[a]
    if flat:  # heading only: the primary vector in the floor plane, twist from straight up
        primary = primary * np.array([1.0, 1.0, 0.0])
        return frame(primary, np.broadcast_to(UP, primary.shape))
    fallback = None if fb is None else joints[fb[1]] - joints[fb[0]]
    return frame(primary, joints[d] - joints[c], fallback)


def leg_length(joints: dict[str, np.ndarray]) -> float:
    lengths = [np.linalg.norm(joints[f"knee.{s}"] - joints[f"hip.{s}"], axis=-1)
               + np.linalg.norm(joints[f"ank.{s}"] - joints[f"knee.{s}"], axis=-1) for s in ("L", "R")]
    return float(np.nanmedian(np.concatenate([np.atleast_1d(v) for v in lengths])))


@dataclass(frozen=True)
class RestBone:
    name: str
    parent: str | None
    matrix: np.ndarray
    """4x4 rest matrix in armature space (Blender's `bone.matrix_local`)."""
    tail: np.ndarray


def solve(rest: list[RestBone], source: dict[str, np.ndarray], frames: int) -> tuple[dict[str, np.ndarray], float]:
    """Pose-space basis matrices (bone -> frames x 4 x 4) for every bone in `BONES`, and the root scale.

    `rest` is in parent-before-child order. A bone whose joints are NaN on a frame keeps its rest
    rotation relative to its parent on that frame.
    """
    by_name = {b.name: b for b in rest}
    heads = {b.name: b.matrix[:3, 3] for b in rest}
    tails = {b.name: b.tail for b in rest}
    target = target_joints(heads, tails)
    scale = leg_length(target) / leg_length(source)
    pose: dict[str, np.ndarray] = {}
    basis: dict[str, np.ndarray] = {}
    for bone in rest:
        if bone.parent is None:
            attached = np.broadcast_to(bone.matrix, (frames, 4, 4)).copy()
        else:
            parent = by_name[bone.parent]
            attached = pose[bone.parent] @ (np.linalg.inv(parent.matrix) @ bone.matrix)
        if bone.name not in BONES:
            pose[bone.name] = attached
            continue
        spec = BONES[bone.name]
        flat = bone.name in FLAT
        actor = bone_frame(source, spec, flat)
        rest_frame = bone_frame(target, spec, flat)
        rotation = actor @ rest_frame.T @ bone.matrix[:3, :3]
        desired = attached.copy()
        ok = ~np.isnan(rotation).any(axis=(1, 2))
        desired[ok, :3, :3] = rotation[ok]
        if bone.name == ROOT:
            hips = source["hips"] * scale
            seen = ~np.isnan(hips).any(axis=1)
            desired[seen, :3, 3] = hips[seen]
        pose[bone.name] = desired
        basis[bone.name] = np.linalg.inv(attached) @ desired
    lift = foot_lift(pose, by_name)
    # Moving the root by -lift in world z: its basis translation is in the root bone's rest frame.
    basis[ROOT][:, :3, 3] -= np.linalg.inv(by_name[ROOT].matrix[:3, :3]) @ np.array([0.0, 0.0, lift])
    return basis, scale


def foot_lift(pose: dict[str, np.ndarray], rest: dict[str, RestBone]) -> float:
    """How far above their rest height the lower ankle is, at its lowest over the take (m)."""
    left, right = (pose[f"foot.{s}"][:, 2, 3] - rest[f"foot.{s}"].matrix[2, 3] for s in ("L", "R"))
    return float(np.nanpercentile(np.minimum(left, right), CONTACT_PERCENTILE))


def quaternions(matrices: np.ndarray) -> np.ndarray:
    """frames x 4 (w, x, y, z) from frames x 3 x 3, sign-continuous over time."""
    m = matrices
    q = np.empty((len(m), 4))
    for i, r in enumerate(m):
        t = np.trace(r)
        if t > 0:
            s = np.sqrt(t + 1.0) * 2
            q[i] = (0.25 * s, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s)
        elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
            s = np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
            q[i] = ((r[2, 1] - r[1, 2]) / s, 0.25 * s, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s)
        elif r[1, 1] > r[2, 2]:
            s = np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
            q[i] = ((r[0, 2] - r[2, 0]) / s, (r[0, 1] + r[1, 0]) / s, 0.25 * s, (r[1, 2] + r[2, 1]) / s)
        else:
            s = np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
            q[i] = ((r[1, 0] - r[0, 1]) / s, (r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, 0.25 * s)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    for i in range(1, len(q)):
        if np.dot(q[i], q[i - 1]) < 0:
            q[i] = -q[i]
    return q
