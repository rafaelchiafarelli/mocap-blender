"""tour.vertex_tour: the platter walks from a vertex to its nearest neighbour."""

import pytest

np = pytest.importorskip("numpy")  # in Blender's Python; the same checks run in blender_smoke.py

from control_surface.tour import TOUR_MAX, vertex_tour  # noqa: E402


def test_starts_at_the_vertex_nearest_the_start_and_walks_to_neighbours():
    co = np.array([[0, 0, 0], [10, 0, 0], [1, 0, 0], [9, 0, 0], [2, 0, 0]], dtype=float)
    assert vertex_tour(co, (0.1, 0, 0)) == [0, 2, 4, 3, 1]


def test_every_vertex_once():
    co = np.random.default_rng(1).random((200, 3))
    order = vertex_tour(co, (0, 0, 0))
    assert sorted(order) == list(range(200))


def test_empty_and_big_meshes():
    assert vertex_tour(np.empty((0, 3)), (0, 0, 0)) == []
    big = np.zeros((TOUR_MAX + 1, 3))
    assert vertex_tour(big, (0, 0, 0)) == list(range(TOUR_MAX + 1))
