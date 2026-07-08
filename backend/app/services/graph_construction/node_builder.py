"""
Node construction stage.

Phase 5's pipe segments are independent straight runs - two segments
that physically meet at an elbow/tee/flange almost never share an
*exactly* equal endpoint coordinate (skeletonization and Hough fitting
both introduce a few pixels of noise). This stage clusters endpoints
that lie within `snap_tolerance_px` of each other into a single graph
node, so the resulting graph actually has junctions instead of a pile
of disconnected line fragments.

Pure geometry (union-find over endpoint coordinates) - no learned model,
per project rules.
"""
from collections import defaultdict
from dataclasses import dataclass

from app.services.pipe_extraction.polyline import PipeSegment

Point = tuple[float, float]

DEFAULT_SNAP_TOLERANCE_PX = 12.0


@dataclass
class EdgeEndpoints:
    """One Phase 5 pipe segment, resolved to the two graph node ids it connects."""

    start_node_id: int
    end_node_id: int
    segment: PipeSegment


class _UnionFind:
    def __init__(self, size: int):
        self._parent = list(range(size))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def _distance(p1: Point, p2: Point) -> float:
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def build_nodes(
    segments: list[PipeSegment], snap_tolerance_px: float = DEFAULT_SNAP_TOLERANCE_PX
) -> tuple[dict[int, Point], list[EdgeEndpoints]]:
    """
    Cluster every segment endpoint into a shared node when two endpoints
    lie within `snap_tolerance_px` of each other, then resolve each
    segment to the (start_node_id, end_node_id) pair it connects.

    Returns (node_positions, edges) where node_positions maps node id ->
    centroid (x, y) of every endpoint clustered into it.
    """
    if not segments:
        return {}, []

    points: list[Point] = []
    for seg in segments:
        points.append(seg.start)
        points.append(seg.end)

    n = len(points)
    uf = _UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if _distance(points[i], points[j]) <= snap_tolerance_px:
                uf.union(i, j)

    root_to_node_id: dict[int, int] = {}
    point_to_node_id: list[int] = [0] * n
    for i in range(n):
        root = uf.find(i)
        if root not in root_to_node_id:
            root_to_node_id[root] = len(root_to_node_id)
        point_to_node_id[i] = root_to_node_id[root]

    sums: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    for i, point in enumerate(points):
        node_id = point_to_node_id[i]
        bucket = sums[node_id]
        bucket[0] += point[0]
        bucket[1] += point[1]
        bucket[2] += 1

    node_positions: dict[int, Point] = {
        node_id: (bucket[0] / bucket[2], bucket[1] / bucket[2]) for node_id, bucket in sums.items()
    }

    edges: list[EdgeEndpoints] = []
    for idx, seg in enumerate(segments):
        start_node_id = point_to_node_id[2 * idx]
        end_node_id = point_to_node_id[2 * idx + 1]
        edges.append(EdgeEndpoints(start_node_id=start_node_id, end_node_id=end_node_id, segment=seg))

    return node_positions, edges
