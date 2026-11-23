from control_surface import grid_sizes as g


def test_ends_and_middle():
    assert g.SIZES[g.pick(0)] == 0.001
    assert g.SIZES[g.pick(127)] == 10.0
    assert g.SIZES[g.pick(64)] == 0.1


def test_every_size_reachable():
    assert {g.pick(v) for v in range(128)} == set(range(len(g.SIZES)))


def test_hysteresis_keeps_size_at_a_boundary():
    # boundary between index 0 and 1 is at value 127/24 ≈ 5.3
    assert g.pick(5) == 0 and g.pick(6) == 1
    assert g.pick(6, current=0) == 0      # jitter just past the boundary: kept
    assert g.pick(5, current=1) == 1
    assert g.pick(8, current=0) == 1      # clearly past it: changes
    assert g.pick(127, current=0) == 12


def test_nearest_and_label():
    assert g.SIZES[g.nearest(1.0)] == 1.0
    assert g.SIZES[g.nearest(0.04)] == 0.05
    assert g.nearest(0) == g.SIZES.index(1.0)
    assert [g.label(s) for s in (0.001, 0.005, 0.02, 0.5, 1.0, 10.0)] == \
        ["1 mm", "5 mm", "2 cm", "50 cm", "1 m", "10 m"]
