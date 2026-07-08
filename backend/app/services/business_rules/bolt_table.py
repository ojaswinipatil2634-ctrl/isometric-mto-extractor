"""
Simplified flange-bolting lookup table.

Real bolt count/diameter selection for a flanged joint comes from
ASME B16.5 (NPS 1/2 through 24) or B16.47 (larger sizes) tables, keyed
by NPS and pressure rating class, and gasket dimensions additionally
depend on facing type. Reproducing the full authoritative standard is
out of scope for this build - this is a small, illustrative subset
covering common NPS values at Class 150 and Class 300.

IMPORTANT: this table is for demonstration purposes in this codebase,
not a substitute for the governing piping spec. Anyone using generated
hardware quantities in a real MTO must verify bolt count/size against
the actual ASME B16.5/B16.47 tables (or the project's piping
specification) before procurement - this module never claims
authoritative accuracy, and every non-exact-match lookup is flagged
`is_estimated=True` rather than silently presented as precise.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class BoltSpec:
    bolt_count: int
    bolt_diameter_in: str  # nominal bolt diameter, e.g. '5/8"'


# (nps_inches, rating_class) -> BoltSpec. Values are illustrative and
# approximate common ASME B16.5 Class 150/300 practice - see module
# docstring.
_BOLT_TABLE: dict[tuple[float, int], BoltSpec] = {
    (0.5, 150): BoltSpec(4, '1/2"'),
    (0.75, 150): BoltSpec(4, '1/2"'),
    (1.0, 150): BoltSpec(4, '1/2"'),
    (1.5, 150): BoltSpec(4, '1/2"'),
    (2.0, 150): BoltSpec(4, '5/8"'),
    (3.0, 150): BoltSpec(4, '5/8"'),
    (4.0, 150): BoltSpec(8, '5/8"'),
    (6.0, 150): BoltSpec(8, '3/4"'),
    (8.0, 150): BoltSpec(8, '3/4"'),
    (10.0, 150): BoltSpec(12, '7/8"'),
    (12.0, 150): BoltSpec(12, '7/8"'),
    (0.5, 300): BoltSpec(4, '1/2"'),
    (1.0, 300): BoltSpec(4, '5/8"'),
    (2.0, 300): BoltSpec(8, '5/8"'),
    (3.0, 300): BoltSpec(8, '3/4"'),
    (4.0, 300): BoltSpec(8, '3/4"'),
    (6.0, 300): BoltSpec(12, '3/4"'),
    (8.0, 300): BoltSpec(12, '7/8"'),
}

_DEFAULT_BOLT_SPEC = BoltSpec(4, '5/8"')


def lookup_bolt_spec(nps_inches: float | None, rating_class: int | None) -> tuple[BoltSpec, bool]:
    """
    Look up the bolt count/diameter for a flanged joint.

    Returns (spec, is_estimated). `is_estimated=True` means the exact
    (NPS, rating class) pair wasn't found in the table (or wasn't
    available at all from OCR) and a conservative default was
    substituted - this is surfaced to the caller rather than silently
    presented as an exact match.
    """
    if nps_inches is not None and rating_class is not None:
        spec = _BOLT_TABLE.get((nps_inches, rating_class))
        if spec is not None:
            return spec, False
    return _DEFAULT_BOLT_SPEC, True
