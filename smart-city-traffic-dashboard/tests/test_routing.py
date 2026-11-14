"""Tests for src/routing.py using a small synthetic road grid (no internet needed)."""

import networkx as nx
import pytest

from src import routing as rt


class FakeGeom:
    """Mimics a shapely LineString (only .coords is needed)."""
    def __init__(self, coords):
        self.coords = coords


def make_grid(n=5, step=0.01):
    """5x5 grid of roads, both directions.

    Row 4 is a slow 'living_street' (shortest but slow).
    Row 2 is a 'primary' road (longer way round but faster).
    """
    g = nx.MultiDiGraph()
    nid = lambda i, j: i * 10 + j  # noqa: E731
    for i in range(n):
        for j in range(n):
            g.add_node(nid(i, j), y=25.30 + i * step, x=82.95 + j * step)

    def add(a, b, cls):
        la, lo = g.nodes[a]["y"], g.nodes[a]["x"]
        lb, lob = g.nodes[b]["y"], g.nodes[b]["x"]
        length = float(rt.haversine_m(la, lo, lb, lob))
        for u, v in ((a, b), (b, a)):
            g.add_edge(u, v, length=length, highway=cls, name=f"Road {a}-{b}")

    for i in range(n):
        for j in range(n):
            if j + 1 < n:
                add(nid(i, j), nid(i, j + 1), "living_street" if i == 4 else ("primary" if i == 2 else "residential"))
            if i + 1 < n:
                add(nid(i, j), nid(i + 1, j), "residential")
    return g


@pytest.fixture(scope="module")
def rg():
    return rt.build_road_graph(make_grid(), "drive")


def test_haversine_one_degree_latitude():
    assert abs(float(rt.haversine_m(25.0, 82.0, 26.0, 82.0)) - 111_195) < 300


def test_speed_estimates():
    assert rt._edge_speed_kph("primary", None, "drive") == 28
    assert rt._edge_speed_kph("primary", "20", "drive") == 20      # tagged limit is lower
    assert rt._edge_speed_kph("primary", "80", "drive") == 28      # assumption caps it
    assert rt._edge_speed_kph("residential", "['30','40']", "drive") == 15
    assert rt._edge_speed_kph("primary", None, "walk") == rt.WALK_SPEED_KPH
    assert rt._parse_speed("30 mph") == pytest.approx(48.27, abs=0.1)
    assert rt._parse_speed("none") is None


def test_nearest_node_and_snap_distance(rg):
    node, dist = rt.nearest_node(rg, 25.3001, 82.9501)
    assert node == 0 and dist < 20
    _, far = rt.nearest_node(rg, 25.30, 83.50)
    assert far > 50_000


def test_shortest_uses_real_edge_lengths_not_straight_line(rg):
    routes = rt.find_routes(rg, 40, 44)       # along the slow bottom row
    short = routes[0]
    assert short.nodes == [40, 41, 42, 43, 44]
    expected = sum(rg.graph[u][v]["length"] for u, v in zip(short.nodes[:-1], short.nodes[1:]))
    assert short.length_m == pytest.approx(expected)


def test_fastest_differs_from_shortest(rg):
    routes = rt.find_routes(rg, 40, 44)
    keys = [r.key for r in routes]
    assert keys[0] == "shortest" and keys[1] == "fastest"
    short, fast = routes[0], routes[1]
    assert fast.length_m >= short.length_m
    assert fast.free_flow_s < short.free_flow_s


def test_alternatives_are_distinct_and_bounded(rg):
    routes = rt.find_routes(rg, 0, 44, max_alternatives=2)
    alts = [r for r in routes if r.key.startswith("alt")]
    assert len(alts) == 2
    base = routes[0].length_m
    for a in alts:
        assert a.length_m <= 1.6 * base + 1
        for other in routes:
            if other is not a:
                assert a.nodes != other.nodes
                assert rt._overlap(rg.graph, a.nodes, other.nodes) < 0.85


def test_zero_alternatives_requested(rg):
    routes = rt.find_routes(rg, 0, 44, max_alternatives=0)
    assert not any(r.key.startswith("alt") for r in routes)


def test_same_node_raises(rg):
    with pytest.raises(rt.RoutingError):
        rt.find_routes(rg, 0, 0)


def test_disconnected_destination_raises():
    g = make_grid()
    g.add_node(999, y=25.5, x=83.2)           # isolated, no roads
    rg2 = rt.build_road_graph(g, "drive")
    with pytest.raises(rt.RoutingError):
        rt.find_routes(rg2, 0, 999)


def test_geometry_is_oriented_and_stitched():
    g = nx.MultiDiGraph()
    g.add_node(1, y=25.30, x=82.95)
    g.add_node(2, y=25.31, x=82.96)
    # geometry stored in the WRONG direction (2 -> 1 ordering) with a bend
    geom = FakeGeom([(82.96, 25.31), (82.953, 25.306), (82.95, 25.30)])
    g.add_edge(1, 2, length=1500.0, highway="primary", geometry=geom)
    g.add_edge(2, 1, length=1500.0, highway="primary", geometry=FakeGeom(list(reversed(geom.coords))))
    rg2 = rt.build_road_graph(g, "drive")
    r = rt.find_routes(rg2, 1, 2, max_alternatives=0)[0]
    assert r.latlons[0] == (25.30, 82.95) and r.latlons[-1] == (25.31, 82.96)
    assert len(r.latlons) == 3


def test_road_class_breakdown_and_main_share(rg):
    short = rt.find_routes(rg, 20, 24, max_alternatives=0)[0]   # straight along the primary row
    assert short.class_m.get("primary", 0) == pytest.approx(short.length_m)
    assert short.main_road_share == pytest.approx(1.0)


def test_congestion_multiplier_range():
    assert rt.congestion_multiplier(0) == 1.0
    assert rt.congestion_multiplier(80) == pytest.approx(1.8)
    assert rt.congestion_multiplier(500) == 2.0


def test_bbox_covers_places_and_roads(tmp_path):
    f = tmp_path / "roads.geojson"
    f.write_text('{"features":[{"geometry":{"coordinates":[[82.9,25.2],[83.1,25.4]]}}]}')
    l, b, r, t = rt.compute_bbox(f, {"x": (25.5, 83.2)}, pad=0.01)
    assert l < 82.9 and b < 25.2 and r > 83.2 and t > 25.5
