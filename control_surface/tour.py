"""Vertex order for picking a 3D cursor vertex with the platter (task 49). Pure (numpy)."""

import numpy as np

TOUR_MAX = 5000  # nearest-neighbour order up to this many vertices; index order above


def vertex_tour(co, start):
    """Vertex indices in a nearest-neighbour walk from the vertex nearest start,
    so the platter goes from a vertex to a neighbour, not by the mesh's numbering."""
    n = len(co)
    if n == 0:
        return []
    if n > TOUR_MAX:
        return list(range(n))
    left = np.ones(n, dtype=bool)
    i = int(np.argmin(np.linalg.norm(co - np.asarray(start, dtype=np.float64), axis=1)))
    order = []
    for _ in range(n):
        order.append(i)
        left[i] = False
        if not left.any():
            break
        d = np.linalg.norm(co - co[i], axis=1)
        d[~left] = np.inf
        i = int(np.argmin(d))
    return order
