"""
Graph-based business rule checks.

All checks here are deterministic graph/topology reasoning over Phase
6's constructed graph (nodes, edges, degrees, and best-effort fitting
associations) - no learned model, no Gemini, per project-wide rules.
Each check only flags a violation it can actually justify from the
graph structure; it never guesses at a defect that isn't visible in
the data.
"""
from dataclasses import dataclass

from app.services.graph_construction.fitting_association import FittingMatch

MIN_REAL_PIPE_LENGTH_PX = 5.0


@dataclass
class RuleViolation:
    rule_code: str
    severity: str  # "warning" | "error"
    message: str
    node_ids: list[int]


def check_missing_fittings(
    branch_node_ids: list[int], fitting_by_node: dict[int, FittingMatch]
) -> list[RuleViolation]:
    """A branch point (3+ connected pipe runs) with no detected fitting
    nearby usually means a tee/cross symbol was missed by Phase 4."""
    return [
        RuleViolation(
            rule_code="MISSING_FITTING",
            severity="warning",
            message=(
                f"Node {node_id} is a branch point (3+ connected pipe runs) with no "
                "detected fitting nearby - a tee or cross symbol may have been missed."
            ),
            node_ids=[node_id],
        )
        for node_id in branch_node_ids
        if node_id not in fitting_by_node
    ]


def check_unterminated_pipes(
    dead_end_node_ids: list[int], fitting_by_node: dict[int, FittingMatch]
) -> list[RuleViolation]:
    """A pipe dead end with no detected terminating fitting (cap,
    flange, valve) means the run appears to just stop on the drawing."""
    return [
        RuleViolation(
            rule_code="UNTERMINATED_PIPE",
            severity="warning",
            message=(
                f"Node {node_id} is a pipe dead end with no detected terminating fitting "
                "(cap, flange, valve) - the run may be incomplete on the drawing, or the "
                "terminating symbol wasn't detected."
            ),
            node_ids=[node_id],
        )
        for node_id in dead_end_node_ids
        if node_id not in fitting_by_node
    ]


def check_invalid_reducers(
    fitting_by_node: dict[int, FittingMatch], node_degrees: dict[int, int]
) -> list[RuleViolation]:
    """A reducer must sit between exactly one upstream and one
    downstream run - anything else is topologically invalid for what
    the symbol represents (a dead-end reducer, or one at a branch)."""
    violations: list[RuleViolation] = []
    for node_id, fitting in fitting_by_node.items():
        if fitting.class_name != "reducer":
            continue
        degree = node_degrees.get(node_id, 0)
        if degree != 2:
            violations.append(
                RuleViolation(
                    rule_code="INVALID_REDUCER",
                    severity="error",
                    message=(
                        f"Node {node_id} is detected as a reducer but connects to {degree} "
                        "pipe run(s) - a reducer must sit between exactly one upstream and "
                        "one downstream run."
                    ),
                    node_ids=[node_id],
                )
            )
    return violations


def check_impossible_connections(
    edges: list[tuple[int, int, dict]],
    fitting_by_node: dict[int, FittingMatch],
    min_length_px: float = MIN_REAL_PIPE_LENGTH_PX,
) -> list[RuleViolation]:
    """Two fittings joined by a near-zero-length pipe run generally
    can't be physically connected with no pipe spacing between them -
    likely two detections resolved to adjacent nodes that are really
    the same joint."""
    violations: list[RuleViolation] = []
    seen: set[tuple[int, int]] = set()

    for u, v, data in edges:
        if data["length_px"] >= min_length_px:
            continue
        if u not in fitting_by_node or v not in fitting_by_node:
            continue

        pair = tuple(sorted((u, v)))
        if pair in seen:
            continue
        seen.add(pair)

        violations.append(
            RuleViolation(
                rule_code="IMPOSSIBLE_CONNECTION",
                severity="error",
                message=(
                    f"Nodes {u} ({fitting_by_node[u].class_name}) and {v} "
                    f"({fitting_by_node[v].class_name}) are connected by a near-zero-length "
                    f"run ({data['length_px']:.1f}px) - two fittings generally can't be "
                    "joined with no pipe spacing between them."
                ),
                node_ids=[u, v],
            )
        )

    return violations
