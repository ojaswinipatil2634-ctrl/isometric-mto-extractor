from app.services.business_rules.bolt_table import lookup_bolt_spec


def test_exact_match_is_not_estimated():
    spec, is_estimated = lookup_bolt_spec(6.0, 150)

    assert is_estimated is False
    assert spec.bolt_count == 8
    assert spec.bolt_diameter_in == '3/4"'


def test_unknown_combination_falls_back_to_default():
    spec, is_estimated = lookup_bolt_spec(37.0, 150)

    assert is_estimated is True
    assert spec.bolt_count == 4
    assert spec.bolt_diameter_in == '5/8"'


def test_missing_nps_falls_back_to_default():
    spec, is_estimated = lookup_bolt_spec(None, 150)

    assert is_estimated is True


def test_missing_rating_class_falls_back_to_default():
    spec, is_estimated = lookup_bolt_spec(6.0, None)

    assert is_estimated is True


def test_class_300_lookup():
    spec, is_estimated = lookup_bolt_spec(4.0, 300)

    assert is_estimated is False
    assert spec.bolt_count == 8
    assert spec.bolt_diameter_in == '3/4"'
