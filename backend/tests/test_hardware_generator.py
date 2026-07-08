from app.services.business_rules.hardware_generator import generate_hardware_for_flanges


def test_no_flanges_returns_empty():
    items = generate_hardware_for_flanges([], 6.0, 150)

    assert items == []


def test_generates_gasket_stud_bolt_and_nut_per_flange():
    items = generate_hardware_for_flanges([5], 6.0, 150)

    by_type = {item.item_type: item for item in items}
    assert by_type["gasket"].quantity == 1
    assert by_type["gasket"].node_id == 5
    assert by_type["stud_bolt"].quantity == 8
    assert by_type["stud_bolt"].size == '3/4"'
    assert by_type["nut"].quantity == 16  # 2 nuts per stud bolt
    assert all(not item.is_estimated for item in items)


def test_generates_hardware_for_multiple_flanges_independently():
    items = generate_hardware_for_flanges([1, 2], 2.0, 150)

    gaskets = [item for item in items if item.item_type == "gasket"]
    assert len(gaskets) == 2
    assert {g.node_id for g in gaskets} == {1, 2}


def test_missing_nps_or_class_flags_estimated():
    items = generate_hardware_for_flanges([1], None, None)

    assert all(item.is_estimated for item in items)
    assert items[0].size == "unknown NPS"
