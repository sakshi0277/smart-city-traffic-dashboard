"""Road-network routing logic (no Streamlit code, so it is easy to test).

DATA LABELS
  * Road geometry and road distances  -> REAL (OpenStreetMap)
  * Travel times                      -> ESTIMATED (assumed average speeds)
  * Optional congestion multiplier    -> SIMULATED (never live traffic)
"""

from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import networkx as nx
import numpy as np

from src.config import get_path

EARTH_RADIUS_M = 6_371_000.0

# ---------------------------------------------------------------------------
# ESTIMATED average speeds (km/h). These are OUR ASSUMPTIONS for city driving,
# lower than posted limits because of junctions, lanes and mixed traffic.
# They are NOT measured and NOT live.
# ---------------------------------------------------------------------------
CAR_SPEEDS_KPH = {
    "motorway": 60, "trunk": 40, "primary": 28, "secondary": 24, "tertiary": 20,
    "unclassified": 18, "residential": 15, "living_street": 8, "service": 10,
}
CAR_DEFAULT_KPH = 15
WALK_SPEED_KPH = 5.0
MAIN_ROAD_CLASSES = {"motorway", "trunk", "primary", "secondary"}


class RoutingError(Exception):
    """A friendly, human-readable routing problem."""


# =============================================================================
# Small helpers
# =============================================================================
def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres. Works for numbers and numpy arrays.

    Used ONLY to snap a place to its nearest road node, never as a route distance.
    """
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def _first(value):
    """OSM values are sometimes lists (or text that looks like a list)."""
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    if isinstance(value, str) and value.startswith("["):
        try:
            parsed = ast.literal_eval(value)
            return parsed[0] if parsed else None
        except (ValueError, SyntaxError):
            return value
    return value


def _road_class(value) -> str:
    v = _first(value)
    return str(v).replace("_link", "").lower() if v else "unknown"


def _parse_speed(value):
    """Read a speed such as '40' or '30 mph' from OSM maxspeed. None if unusable."""
    v = _first(value)
    if v is None:
        return None
    text = str(v)
    m = re.search(r"\d+(\.\d+)?", text)
    if not m:
        return None
    speed = float(m.group()) * (1.609 if "mph" in text.lower() else 1.0)
    return speed if 3 <= speed <= 130 else None


def _edge_speed_kph(road_class: str, maxspeed, mode: str) -> float:
    """ESTIMATED speed on one road segment."""
    if mode == "walk":
        return WALK_SPEED_KPH
    assumed = CAR_SPEEDS_KPH.get(road_class, CAR_DEFAULT_KPH)
    tagged = _parse_speed(maxspeed)
    # If OSM says the limit is lower than our assumption, respect it.
    return float(min(tagged, assumed)) if tagged else float(assumed)


def congestion_multiplier(index: float) -> float:
    """ASSUMPTION: SIMULATED congestion index 0-100 -> travel time x (1.0 to 2.0)."""
    return 1.0 + max(0.0, min(100.0, index)) / 100.0


# =============================================================================
# Files and download (done ONCE, then cached on disk)
# =============================================================================
def graph_file(mode: str) -> Path:
    return get_path("raw") / f"varanasi_{mode}_graph.graphml"


def meta_file(mode: str) -> Path:
    return get_path("raw") / f"varanasi_{mode}_graph_meta.json"


def graph_exists(mode: str) -> bool:
    return graph_file(mode).exists()


def _flatten_coords(obj):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            yield obj
        else:
            for item in obj:
                yield from _flatten_coords(item)


def compute_bbox(roads_file: Path, points: dict, pad: float = 0.02):
    """(left, bottom, right, top) covering the saved Traffic Map roads AND all places."""
    lons = [lon for _, lon in points.values()]
    lats = [lat for lat, _ in points.values()]
    if roads_file.exists():
        try:
            data = json.loads(roads_file.read_text(encoding="utf-8"))
            for feat in data.get("features", []):
                for c in _flatten_coords(feat["geometry"]["coordinates"]):
                    lons.append(c[0])
                    lats.append(c[1])
        except (OSError, ValueError, KeyError):
            pass  # fall back to the places only
    return (min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad)


def download_graph(mode: str, bbox) -> dict:
    """Download a routing graph ONCE from OpenStreetMap and save it to data/raw/."""
    import osmnx as ox  # imported here so the rest of the module stays light

    if mode not in ("drive", "walk"):
        raise ValueError("mode must be 'drive' or 'walk'")
    ox.settings.use_cache = True
    ox.settings.log_console = False
    graph = ox.graph_from_bbox(bbox, network_type=mode, simplify=True, retain_all=False)

    path = graph_file(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, path)
    meta = {
        "label": "REAL",
        "source": "OpenStreetMap contributors (via OSMnx " + ox.__version__ + ")",
        "licence": "ODbL 1.0",
        "network_type": mode,
        "bbox_left_bottom_right_top": [round(v, 5) for v in bbox],
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "downloaded_on": date.today().isoformat(),
    }
    meta_file(mode).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


# =============================================================================
# Road graph
# =============================================================================
@dataclass
class RoadGraph:
    mode: str
    graph: nx.DiGraph
    node_list: list
    lats: np.ndarray
    lons: np.ndarray


def build_road_graph(multi: nx.MultiDiGraph, mode: str) -> RoadGraph:
    """Convert an OSMnx graph into a simple directed graph with our attributes."""
    dg = nx.DiGraph()
    for n, d in multi.nodes(data=True):
        dg.add_node(n, lat=float(d["y"]), lon=float(d["x"]))

    best = {}  # keep the SHORTEST of any parallel edges between two nodes
    for u, v, data in multi.edges(data=True):
        if u == v:
            continue
        length = float(data.get("length") or 0.0)
        if length <= 0:
            length = float(haversine_m(dg.nodes[u]["lat"], dg.nodes[u]["lon"],
                                       dg.nodes[v]["lat"], dg.nodes[v]["lon"]))
        if (u, v) not in best or length < best[(u, v)][0]:
            best[(u, v)] = (length, data)

    for (u, v), (length, data) in best.items():
        cls = _road_class(data.get("highway"))
        speed = _edge_speed_kph(cls, data.get("maxspeed"), mode)
        geom = data.get("geometry")
        coords = tuple(geom.coords) if geom is not None and hasattr(geom, "coords") else None
        name = _first(data.get("name"))
        dg.add_edge(
            u, v, length=length, speed_kph=speed, time_s=length / (speed / 3.6),
            road_class=cls, name=name if isinstance(name, str) else "Unnamed road", coords=coords,
        )

    nodes = list(dg.nodes)
    return RoadGraph(
        mode=mode, graph=dg, node_list=nodes,
        lats=np.array([dg.nodes[n]["lat"] for n in nodes]),
        lons=np.array([dg.nodes[n]["lon"] for n in nodes]),
    )


def load_road_graph(mode: str) -> RoadGraph:
    """Read the saved GraphML file (no internet needed)."""
    import osmnx as ox

    path = graph_file(mode)
    if not path.exists():
        raise RoutingError(f"The {mode} road network has not been downloaded yet.")
    return build_road_graph(ox.load_graphml(path), mode)


def nearest_node(rg: RoadGraph, lat: float, lon: float):
    """Nearest road node to a place. Returns (node_id, snap_distance_in_metres)."""
    dist = haversine_m(lat, lon, rg.lats, rg.lons)
    i = int(np.argmin(dist))
    return rg.node_list[i], float(dist[i])


# =============================================================================
# Routes
# =============================================================================
@dataclass
class Route:
    key: str
    label: str
    description: str
    nodes: list
    length_m: float
    free_flow_s: float          # ESTIMATED, before any congestion multiplier
    latlons: list               # [(lat, lon), ...] REAL road geometry
    class_m: dict               # metres per road class

    @property
    def length_km(self) -> float:
        return self.length_m / 1000.0

    @property
    def main_road_share(self) -> float:
        total = sum(self.class_m.values()) or 1.0
        return sum(m for c, m in self.class_m.items() if c in MAIN_ROAD_CLASSES) / total


def _edge_latlons(g: nx.DiGraph, u, v):
    """Points of one road segment, oriented from u to v."""
    coords = g[u][v].get("coords")
    nu, nv = g.nodes[u], g.nodes[v]
    if not coords:
        return [(nu["lat"], nu["lon"]), (nv["lat"], nv["lon"])]
    pts = [(c[1], c[0]) for c in coords]
    d_start = (pts[0][0] - nu["lat"]) ** 2 + (pts[0][1] - nu["lon"]) ** 2
    d_end = (pts[-1][0] - nu["lat"]) ** 2 + (pts[-1][1] - nu["lon"]) ** 2
    return pts[::-1] if d_end < d_start else pts


def make_route(g: nx.DiGraph, nodes: list, key: str, label: str, description: str) -> Route:
    length = time_s = 0.0
    class_m: dict = {}
    latlons: list = []
    for u, v in zip(nodes[:-1], nodes[1:]):
        e = g[u][v]
        length += e["length"]
        time_s += e["time_s"]
        class_m[e["road_class"]] = class_m.get(e["road_class"], 0.0) + e["length"]
        pts = _edge_latlons(g, u, v)
        latlons.extend(pts[1:] if latlons else pts)
    return Route(key, label, description, list(nodes), length, time_s, latlons, class_m)


def _edge_set(nodes: list) -> set:
    return {frozenset((u, v)) for u, v in zip(nodes[:-1], nodes[1:])}


def _overlap(g: nx.DiGraph, a: list, b: list) -> float:
    """Share (0-1) of the shorter route's length that the two routes have in common."""
    ea, eb = _edge_set(a), _edge_set(b)
    shared = sum(g[u][v]["length"] for u, v in zip(a[:-1], a[1:]) if frozenset((u, v)) in eb)
    la = sum(g[u][v]["length"] for u, v in zip(a[:-1], a[1:]))
    lb = sum(g[u][v]["length"] for u, v in zip(b[:-1], b[1:]))
    return shared / max(min(la, lb), 1e-9)


def _path(g, origin, dest, weight):
    try:
        return nx.shortest_path(g, origin, dest, weight=weight)
    except nx.NetworkXNoPath as err:
        raise RoutingError(
            "No connected road route exists between these two places in the downloaded "
            "network. One of them may sit on a disconnected road fragment."
        ) from err
    except nx.NodeNotFound as err:
        raise RoutingError("A selected place could not be matched to the road network.") from err


def find_routes(rg: RoadGraph, origin, dest, max_alternatives: int = 2,
                max_overlap: float = 0.85, max_detour: float = 1.6,
                penalty: float = 1.6, max_attempts: int = 12) -> list:
    """Shortest route, fastest (estimated) route and alternative routes.

    Alternatives use the "penalty method": edges already used get a higher cost,
    the shortest path is recomputed, and a result is kept only if it is
    different enough and not much longer than the shortest route.
    """
    g = rg.graph
    if origin == dest:
        raise RoutingError("Start and destination are the same road node.")

    shortest_nodes = _path(g, origin, dest, "length")
    fastest_nodes = _path(g, origin, dest, "time_s")
    same = shortest_nodes == fastest_nodes

    routes = [make_route(
        g, shortest_nodes,
        "shortest_fastest" if same else "shortest",
        "Shortest & fastest" if same else "Shortest",
        "Lowest total road distance" + (" (also lowest estimated time)" if same else ""),
    )]
    if not same:
        routes.append(make_route(g, fastest_nodes, "fastest", "Fastest (estimated)",
                                 "Lowest ESTIMATED travel time using assumed average speeds"))

    base_len = routes[0].length_m
    penalties: dict = {}

    def bump(nodes):
        for u, v in zip(nodes[:-1], nodes[1:]):
            penalties[(u, v)] = penalties.get((u, v), 1.0) * penalty
            penalties[(v, u)] = penalties.get((v, u), 1.0) * penalty

    for r in routes:
        bump(r.nodes)

    def cost(u, v, data):
        return data["length"] * penalties.get((u, v), 1.0)

    alternatives = 0
    for _ in range(max_attempts):
        if alternatives >= max_alternatives:
            break
        cand = _path(g, origin, dest, cost)
        cand_len = sum(g[u][v]["length"] for u, v in zip(cand[:-1], cand[1:]))
        if cand_len > max_detour * base_len:
            break  # penalties only make detours longer from here on
        distinct = all(_overlap(g, cand, r.nodes) < max_overlap for r in routes)
        if distinct:
            alternatives += 1
            routes.append(make_route(
                g, cand, f"alt{alternatives}", f"Alternative {alternatives}",
                "Avoids parts of the shortest route (penalty method)",
            ))
        bump(cand)
    return routes
