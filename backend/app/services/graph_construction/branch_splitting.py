"""
Branch-point splitting stage.

Endpoint snapping (node_builder.py) correctly unifies two segments that
meet *end-to-end* (an elbow/corner). It does NOT handle the equally
common case of a branch line teeing into the *middle* of a straight
run - the branch's endpoint lies on the main run's interior, not at
either of the main run's own endpoints, so plain endpoint clustering
would leave the main run and the branch as two disconnected pieces.

This stage finds every such point (one segment's endpoint landing on
another segment's interior line, within tolerance) and splits the
interior segment there, so the branch point becomes a real shared node
once node_builder runs afterward.

`endpoint_margin_px` deliberately excludes points too close to the
target segment's own endpoints - that case is a near-collinear
corner/overlap already handled by endpoint snapping, not a true
mid-span branch, and re-splitting there would just create a spurious
near-zero-length segment.

Deliberately NOT handled: two lines that merely cross in the drawing
with neither's endpoint landing on the other (a bare "+" crossing).
In real isometric drawing convention that represents two unconnected
pipes overlapping in the 2D projection, not a fitting - splitting both
lines there would spuriously merge unrelated runs into one connected
graph. A genuine branch is always drawn with one run's endpoint
touching the other, which is exactly the case this stage does handle.
"""
from dataclasses import replace

from app.services.pipe_extraction.polyline import PipeSegment

DEFAULT_BRANCH_TOLERANCE_PX = 12.0
DEFAULT_ENDPOINT_MARGIN_PX = 15.0


def _try_split(
    segment: PipeSegment, point: tuple[float, float], tolerance_px: float, endpoint_margin_px: float
) -> tuple[PipeSegment, PipeSegment] | None:
    length = segment.length_px
    if length <= 0:
        return None

    dx = (segment.end[0] - segment.start[0]) / length
    dy = (segment.end[1] - segment.start[1]) / length

    vx, vy = point[0] - segment.start[0], point[1] - segment.start[1]
    projection = vx * dx + vy * dy
    perpendicular_distance = abs(vx * -dy + vy * dx)

    if perpendicular_distance > tolerance_px:
        return None
    if projection <= endpoint_margin_px or projection >= length - endpoint_margin_px:
        return None

    split_point = (segment.start[0] + dx * projection, segment.start[1] + dy * projection)

    first = replace(segment, end=split_point, length_px=round(projection, 2))
    second = replace(segment, start=split_point, length_px=round(length - projection, 2))
    return first, second


def split_segments_at_branch_points(
    segments: list[PipeSegment],
    tolerance_px: float = DEFAULT_BRANCH_TOLERANCE_PX,
    endpoint_margin_px: float = DEFAULT_ENDPOINT_MARGIN_PX,
) -> list[PipeSegment]:
    """
    Split any segment whose interior is landed on by another segment's
    endpoint (a T/branch junction), so the junction becomes a real
    shared point once endpoints are clustered into nodes.

    Runs to a fixed point since one split can expose a new endpoint
    that itself lands on a third segment (e.g. a cross/+ junction).
    """
    if not segments:
        return []

    result = list(segments)

    changed = True
    while changed:
        changed = False
        endpoints = [p for seg in result for p in (seg.start, seg.end)]

        for point in endpoints:
            for idx, seg in enumerate(result):
                split = _try_split(seg, point, tolerance_px, endpoint_margin_px)
                if split is not None:
                    result[idx : idx + 1] = list(split)
                    changed = True
                    break
            if changed:
                break

    return result
