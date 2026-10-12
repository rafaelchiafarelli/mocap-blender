import numpy as np
import pytest

from mocap_blender.retarget import BODY, bone_frame, fill_gaps, frame, normalise, quaternions


def rotation(axis, angle):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


def test_frame_is_orthonormal_along_primary():
    f = frame(np.array([0.0, 0, 2]), np.array([1.0, 1, 0]))
    np.testing.assert_allclose(f.T @ f, np.eye(3), atol=1e-12)
    np.testing.assert_allclose(f[:, 0], [0, 0, 1])
    assert np.linalg.det(f) == pytest.approx(1)


def test_rotation_between_frames_is_recovered():
    rng = np.random.default_rng(1)
    joints = {k: rng.normal(size=3) for k in "abcd"}
    r = rotation([1, 2, 3], 0.7)
    moved = {k: r @ v for k, v in joints.items()}
    spec = (("a", "b"), ("c", "d"), None)
    np.testing.assert_allclose(bone_frame(moved, spec) @ bone_frame(joints, spec).T, r, atol=1e-12)


def test_parallel_secondary_uses_the_fallback():
    f = frame(np.array([1.0, 0, 0]), np.array([2.0, 0.01, 0]), np.array([0.0, 0, 1]))
    np.testing.assert_allclose(f[:, 1], [0, 0, 1], atol=1e-12)


def test_fill_gaps_interpolates_and_keeps_never_seen_points():
    p = np.zeros((5, 2, 3))
    p[:, 0, 0] = [0, np.nan, np.nan, 3, 4]
    p[:, 1] = np.nan
    out, n = fill_gaps(p)
    np.testing.assert_allclose(out[:, 0, 0], [0, 1, 2, 3, 4])
    assert np.isnan(out[:, 1]).all() and n == 2


def standing_body(frames=4):
    """MediaPipe body points (mm) of a person standing at the origin, facing -Y, Z up."""
    pts = {"nose": (0, -100, 1650), "ear.L": (80, 0, 1620), "ear.R": (-80, 0, 1620),
           "sho.L": (180, 0, 1450), "sho.R": (-180, 0, 1450), "elb.L": (250, 0, 1150), "elb.R": (-250, 0, 1150),
           "wri.L": (280, -50, 880), "wri.R": (-280, -50, 880), "hip.L": (100, 0, 950), "hip.R": (-100, 0, 950),
           "knee.L": (100, -20, 500), "knee.R": (-100, -20, 500), "ank.L": (100, 0, 80), "ank.R": (-100, 0, 80),
           "heel.L": (100, 60, 40), "heel.R": (-100, 60, 40), "toe.L": (110, -150, 20), "toe.R": (-110, -150, 20)}
    body = np.full((frames, 33, 3), np.nan)
    for name, i in BODY.items():
        body[:, i] = pts[name]
    hand = np.zeros((frames, 21, 3))
    return body, hand, hand.copy()


def test_normalise_faces_minus_y_with_feet_on_the_floor():
    body, lh, rh = standing_body()
    r = rotation([0.3, 1, 0.2], 2.0)  # camera-like world: arbitrary rotation and offset
    moved = body @ r.T + np.array([500, -300, 2500])
    n = normalise(moved, lh @ r.T, rh @ r.T, ground_plane=False)
    j = n.joints
    assert np.allclose(j["hips"][:, :2], 0, atol=1e-9)
    assert j["sho.L"][0, 0] > 0 > j["sho.R"][0, 0]  # actor's left is +X
    assert j["toe.L"][0, 1] < j["heel.L"][0, 1]  # toes point to -Y
    assert min(j["toe.L"][0, 2], j["toe.R"][0, 2]) == pytest.approx(0, abs=0.03)  # mm -> m, floor at 0
    assert j["shoulders"][0, 2] == pytest.approx(1.43, abs=0.05)


def test_quaternions_match_and_stay_continuous():
    mats = np.stack([rotation([0, 0, 1], a) for a in np.linspace(0, 6, 30)])
    q = quaternions(mats)
    assert (np.sum(q[1:] * q[:-1], axis=1) > 0).all()
    w, x, y, z = q[10]
    assert 2 * np.arctan2(z, w) == pytest.approx(np.linspace(0, 6, 30)[10], abs=1e-9)
