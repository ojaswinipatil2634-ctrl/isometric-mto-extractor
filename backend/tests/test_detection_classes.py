from app.services.detection.classes import CLASS_ID_TO_NAME, CLASS_NAMES


def test_class_names_match_spec_list():
    expected = {
        "elbow", "tee", "reducer", "gate_valve", "globe_valve",
        "check_valve", "flange", "support", "weld",
    }
    assert set(CLASS_NAMES) == expected


def test_class_id_to_name_is_contiguous_from_zero():
    assert sorted(CLASS_ID_TO_NAME.keys()) == list(range(len(CLASS_NAMES)))


def test_class_id_to_name_round_trips_with_class_names_list():
    for i, name in enumerate(CLASS_NAMES):
        assert CLASS_ID_TO_NAME[i] == name
