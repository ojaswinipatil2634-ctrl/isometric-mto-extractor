"""
Polyline extraction stage.

Raw Hough output (hough.py) is noisy for this purpose: a single pipe
run typically comes back as several overlapping/adjacent segments
(gaps at text labels or where a symbol interrupts the skeleton, plus
duplicate near-parallel fragments along a slightly wavy skeleton
line). This stage merges those raw segments into the smallest set of
straight pipe-run polylines that explain them - segments that share
the same orientation, lie on (approximately) the same infinite line,
and are close enough along that line to plausibly be one continuous
run, get merged into one.

This stage only merges collinear segments into longer straight
segments. It deliberately does NOT connect runs of different
orientation into multi-vertex polylines (e.g. a horizontal run meeting
a vertical run at an elbow) - identifying which fitting joins which
runs is graph-level reasoning and belongs to Phase 6 (graph
construction), which will take this phase's straight segments as its
edges.

OpenCV/NumPy geometry only - no learned model is involved in this stage.
"""
import logging
import math
from dataclasses import dataclass

from app.services.pipe_extraction.hough import RawLineSegment

logger = logging.getLogger(__name__)

Point = tuple[float, float]


@dataclass(frozen=True)
class PipeSegment:
    """One merged, straight pipe-run segment."""

    start: Point
    end: Point
    length_px: float
    angle_degrees: float  # normalized to [0, 180)
    orientation: str  # "horizontal" | "vertical" | "diagonal"
    source_segment_count: int  # how many raw Hough segments were merged into this one


def _length(seg: RawLineSegment) -> float:
    return math.hypot(seg.x2 - seg.x1, seg.y2 - seg.y1)


def _angle_degrees(seg: RawLineSegment) -> float:
    """Angle of the segment's direction, normalized to [0, 180) so a
    line and its reverse report the same angle."""
    angle = math.degrees(math.atan2(seg.y2 - seg.y1, seg.x2 - seg.x1))
    return angle % 180.0


def _angle_diff(a: float, b: float) -> float:
    """Smallest difference between two [0, 180)-normalized angles,
    accounting for wraparound at 0/180."""
    diff = abs(a - b) % 180.0
    return min(diff, 180.0 - diff)


def classify_orientation(angle_degrees: float, tolerance_degrees: float = 10.0) -> str:
    """Classify a normalized [0, 180) angle as horizontal, vertical, or
    diagonal. Diagonal covers isometric pipe runs, which are
    conventionally drawn at ~30/60/120/150 degrees."""
    if _angle_diff(angle_degrees, 0.0) <= tolerance_degrees:
        return "horizontal"
    if _angle_diff(angle_degrees, 90.0) <= tolerance_degrees:
        return "vertical"
    return "diagonal"


def _endpoints(seg: RawLineSegment) -> tuple[Point, Point]:
    return (seg.x1, seg.y1), (seg.x2, seg.y2)


def _project_onto_direction(point: Point, origin: Point, unit_dir: tuple[float, float]) -> float:
    """Scalar position of `point` projected onto the line through
    `origin` in direction `unit_dir`."""
    return (point[0] - origin[0]) * unit_dir[0] + (point[1] - origin[1]) * unit_dir[1]


def _perpendicular_distance(point: Point, origin: Point, unit_dir: tuple[float, float]) -> float:
    """Distance from `point` to the infinite line through `origin` in
    direction `unit_dir`."""
    dx, dy = point[0] - origin[0], point[1] - origin[1]
    # Perpendicular component = component along the normal (-dy_dir, dx_dir).
    return abs(dx * -unit_dir[1] + dy * unit_dir[0])


class _MergeGroup:
    """Mutable accumulator for one merged pipe run while candidate
    segments are being folded into it."""

    def __init__(self, seg: RawLineSegment):
        p1, p2 = _endpoints(seg)
        self.origin: Point = p1
        length = _length(seg)
        if length == 0:
            self.unit_dir = (1.0, 0.0)
        else:
            self.unit_dir = ((p2[0] - p1[0]) / length, (p2[1] - p1[1]) / length)
        self.min_proj = 0.0
        self.max_proj = length
        self.angle_degrees = _angle_degrees(seg)
        self.count = 1

    def extremes(self) -> tuple[Point, Point]:
        start = (self.origin[0] + self.unit_dir[0] * self.min_proj, self.origin[1] + self.unit_dir[1] * self.min_proj)
        end = (self.origin[0] + self.unit_dir[0] * self.max_proj, self.origin[1] + self.unit_dir[1] * self.max_proj)
        return start, end

    def try_merge(
        self,
        seg: RawLineSegment,
        angle_tolerance_degrees: float,
        colinear_distance_tolerance_px: float,
        gap_tolerance_px: float,
    ) -> bool:
        seg_angle = _angle_degrees(seg)
        if _angle_diff(self.angle_degrees, seg_angle) > angle_tolerance_degrees:
            return False

        p1, p2 = _endpoints(seg)
        if self._perp_distance(p1) > colinear_distance_tolerance_px:
            return False
        if self._perp_distance(p2) > colinear_distance_tolerance_px:
            return False

        proj1 = _project_onto_direction(p1, self.origin, self.unit_dir)
        proj2 = _project_onto_direction(p2, self.origin, self.unit_dir)
        seg_min, seg_max = min(proj1, proj2), max(proj1, proj2)

        # Overlapping or within gap_tolerance along the shared direction?
        if seg_min > self.max_proj + gap_tolerance_px:
            return False
        if seg_max < self.min_proj - gap_tolerance_px:
            return False

        self.min_proj = min(self.min_proj, seg_min)
        self.max_proj = max(self.max_proj, seg_max)
        self.count += 1
        return True

    def _perp_distance(self, point: Point) -> float:
        return _perpendicular_distance(point, self.origin, self.unit_dir)


def merge_line_segments(
    segments: list[RawLineSegment],
    angle_tolerance_degrees: float = 4.0,
    colinear_distance_tolerance_px: float = 6.0,
    gap_tolerance_px: float = 50.0,
    orientation_tolerance_degrees: float = 10.0,
) -> list[PipeSegment]:
    """
    Merge raw Hough segments that are collinear and close together
    along their shared direction into single straight PipeSegments.

    This runs to a fixed point: repeated passes over the working set,
    absorbing any segment that fits an existing group, until a full
    pass makes no further merges. Small, deterministic inputs (a
    drawing has dozens to low hundreds of raw segments, not millions),
    so the O(n^2)-per-pass approach is simple and fast enough; a
    spatial index would be premature here.

    `gap_tolerance_px` defaults to a fairly generous 50px rather than a
    tight value, for two compounding reasons:
      1. Real interruptions in a pipe run's ink - a dimension label or
         a symbol sitting on top of the line - are a visual break, not
         a physical one, and should still resolve to one continuous
         pipe run.
      2. `cv2.HoughLinesP` is a probabilistic algorithm and routinely
         reports one long, perfectly continuous straight run as
         several adjacent/overlapping segments with small gaps between
         them, even when there's no actual break in the underlying
         skeleton pixels at all.
    A generous default trades a small risk of bridging two genuinely
    separate, precisely collinear pipe runs (rare in practice, and
    something Phase 6's graph/connectivity reasoning can still catch)
    against the much more common failure mode of one physical run
    fragmenting into many spurious segments.
    """
    if not segments:
        return []

    groups: list[_MergeGroup] = [_MergeGroup(segments[0])]

    for seg in segments[1:]:
        groups.append(_MergeGroup(seg))

    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(groups):
            j = i + 1
            while j < len(groups):
                start, end = groups[j].extremes()
                probe = RawLineSegment(start[0], start[1], end[0], end[1])
                if groups[i].try_merge(
                    probe, angle_tolerance_degrees, colinear_distance_tolerance_px, gap_tolerance_px
                ):
                    groups[i].count += groups[j].count - 1  # try_merge already added 1
                    del groups[j]
                    changed = True
                else:
                    j += 1
            i += 1

    results: list[PipeSegment] = []
    for group in groups:
        start, end = group.extremes()
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        angle = group.angle_degrees
        results.append(
            PipeSegment(
                start=start,
                end=end,
                length_px=round(length, 2),
                angle_degrees=round(angle, 2),
                orientation=classify_orientation(angle, orientation_tolerance_degrees),
                source_segment_count=group.count,
            )
        )

    logger.info("Polyline: merged %d raw segment(s) into %d pipe run(s)", len(segments), len(results))
    return results
