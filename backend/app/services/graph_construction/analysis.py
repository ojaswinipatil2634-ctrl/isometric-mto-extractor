"""
Graph analysis stage.

Computes the structural properties Phase 6 is scoped to report:
branch points, dead ends, loops, and connectivity. All of this is
standard graph theory via NetworkX - no learned model, no Gemini.
"""
from dataclasses import dataclass, field

import networkx as nx


@dataclass
class GraphAnalysis:
    branch_node_ids: list[int] = field(default_factory=list)
    dead_end_node_ids: list[int] = field(default_factory=list)
    loops: list[list[int]] = field(default_factory=list)
    connected_components: list[list[int]] = field(default_factory=list)
    is_fully_connected: bool = True


def _simple_graph_for_cycles(graph: nx.MultiGraph) -> nx.Graph:
    """Collapse parallel edges into one for cycle_basis (which expects a
    simple Graph) - the parallel edges themselves are reported as their
    own 2-node loops separately, see `_parallel_edge_loops`."""
    simple = nx.Graph()
    simple.add_nodes_from(graph.nodes())
    simple.add_edges_from(graph.edges())
    return simple


def _parallel_edge_loops(graph: nx.MultiGraph) -> list[list[int]]:
    """Any node pair connected by 2+ distinct pipe segments is itself a
    loop (two different paths between the same two junctions), even
    though a simple-graph cycle basis can't see it once collapsed."""
    loops: list[list[int]] = []
    seen_pairs: set[frozenset] = set()
    for u, v in graph.edges():
        pair = frozenset((u, v))
        if pair in seen_pairs:
            continue
        if graph.number_of_edges(u, v) >= 2:
            loops.append(sorted((u, v)))
            seen_pairs.add(pair)
    return loops


def analyze(graph: nx.MultiGraph) -> GraphAnalysis:
    if graph.number_of_nodes() == 0:
        return GraphAnalysis(is_fully_connected=True)

    degrees = dict(graph.degree())
    branch_node_ids = sorted(n for n, d in degrees.items() if d >= 3)
    dead_end_node_ids = sorted(n for n, d in degrees.items() if d == 1)

    simple = _simple_graph_for_cycles(graph)
    cycle_loops = [sorted(cycle) for cycle in nx.cycle_basis(simple)]
    loops = cycle_loops + _parallel_edge_loops(graph)

    components = [sorted(c) for c in nx.connected_components(graph)]
    components.sort(key=lambda c: c[0] if c else 0)

    return GraphAnalysis(
        branch_node_ids=branch_node_ids,
        dead_end_node_ids=dead_end_node_ids,
        loops=loops,
        connected_components=components,
        is_fully_connected=len(components) <= 1,
    )
