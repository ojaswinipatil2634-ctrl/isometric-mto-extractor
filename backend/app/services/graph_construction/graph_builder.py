"""
Graph construction stage.

Builds a NetworkX MultiGraph from the snapped nodes (node_builder.py)
and Phase 5's pipe segments. A MultiGraph (not a plain Graph) is used
deliberately - two distinct pipe runs can legitimately connect the same
pair of junctions (a short parallel/bypass run, or two segments that
both terminate at the same elbow), and collapsing those into one edge
would silently discard real topology and hide genuine loops.
"""
import networkx as nx

from app.services.graph_construction.node_builder import EdgeEndpoints, Point


def build_graph(node_positions: dict[int, Point], edges: list[EdgeEndpoints]) -> nx.MultiGraph:
    graph = nx.MultiGraph()

    for node_id, (x, y) in node_positions.items():
        graph.add_node(node_id, x=x, y=y)

    for edge in edges:
        seg = edge.segment
        # Skip degenerate self-loops produced when both endpoints of a
        # segment snap into the same node (a near-zero-length artifact,
        # not a real pipe run).
        if edge.start_node_id == edge.end_node_id:
            continue
        graph.add_edge(
            edge.start_node_id,
            edge.end_node_id,
            length_px=seg.length_px,
            angle_degrees=seg.angle_degrees,
            orientation=seg.orientation,
            source_segment_count=seg.source_segment_count,
        )

    return graph
