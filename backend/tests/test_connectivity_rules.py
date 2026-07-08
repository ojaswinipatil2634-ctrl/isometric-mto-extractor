from app.services.business_rules.connectivity_rules import (
    check_impossible_connections,
    check_invalid_reducers,
    check_missing_fittings,
    check_unterminated_pipes,
)
from app.services.graph_construction.fitting_association import FittingMatch


def _fitting(name: str, confidence: float = 0.9, distance: float = 5.0) -> FittingMatch:
    return FittingMatch(class_name=name, confidence=confidence, distance_px=distance)


# --- missing fittings ---

def test_branch_without_fitting_is_flagged():
    violations = check_missing_fittings([3], {})

    assert len(violations) == 1
    assert violations[0].rule_code == "MISSING_FITTING"
    assert violations[0].node_ids == [3]


def test_branch_with_fitting_is_not_flagged():
    violations = check_missing_fittings([3], {3: _fitting("tee")})

    assert violations == []


# --- unterminated pipes ---

def test_dead_end_without_fitting_is_flagged():
    violations = check_unterminated_pipes([7], {})

    assert len(violations) == 1
    assert violations[0].rule_code == "UNTERMINATED_PIPE"


def test_dead_end_with_fitting_is_not_flagged():
    violations = check_unterminated_pipes([7], {7: _fitting("flange")})

    assert violations == []


# --- invalid reducers ---

def test_reducer_with_degree_two_is_valid():
    violations = check_invalid_reducers({4: _fitting("reducer")}, {4: 2})

    assert violations == []


def test_reducer_with_degree_one_is_invalid():
    violations = check_invalid_reducers({4: _fitting("reducer")}, {4: 1})

    assert len(violations) == 1
    assert violations[0].rule_code == "INVALID_REDUCER"


def test_reducer_with_degree_three_is_invalid():
    violations = check_invalid_reducers({4: _fitting("reducer")}, {4: 3})

    assert len(violations) == 1
    assert violations[0].rule_code == "INVALID_REDUCER"


def test_non_reducer_fitting_is_ignored():
    violations = check_invalid_reducers({4: _fitting("flange")}, {4: 1})

    assert violations == []


# --- impossible connections ---

def test_two_fittings_joined_by_near_zero_length_run_flagged():
    edges = [(1, 2, {"length_px": 1.0})]
    fitting_by_node = {1: _fitting("gate_valve"), 2: _fitting("globe_valve")}

    violations = check_impossible_connections(edges, fitting_by_node)

    assert len(violations) == 1
    assert violations[0].rule_code == "IMPOSSIBLE_CONNECTION"
    assert violations[0].node_ids == [1, 2]


def test_fittings_joined_by_normal_length_run_not_flagged():
    edges = [(1, 2, {"length_px": 300.0})]
    fitting_by_node = {1: _fitting("gate_valve"), 2: _fitting("globe_valve")}

    violations = check_impossible_connections(edges, fitting_by_node)

    assert violations == []


def test_near_zero_length_run_without_two_fittings_not_flagged():
    edges = [(1, 2, {"length_px": 1.0})]
    fitting_by_node = {1: _fitting("gate_valve")}  # only one end has a fitting

    violations = check_impossible_connections(edges, fitting_by_node)

    assert violations == []
