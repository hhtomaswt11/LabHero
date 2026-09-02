"""Canonical scientific labels and units for player-visible LabHero output.

Keep units here so reports, simulator panels and mission evidence use the same
terminology. These helpers are presentation-only; they do not alter solver data.
"""

GROWTH_RATE_LABEL = "Predicted growth rate"
GROWTH_RATE_UNIT = "h^-1"
FLUX_UNIT = "mmol gDW^-1 h^-1"
AGGREGATE_FLUX_UNIT = "model flux units"


def label_with_unit(label, unit):
    return f"{label} ({unit})"


def growth_rate_label():
    return label_with_unit(GROWTH_RATE_LABEL, GROWTH_RATE_UNIT)


def flux_label(label):
    return label_with_unit(label, FLUX_UNIT)


def aggregate_flux_label(label):
    return label_with_unit(label, AGGREGATE_FLUX_UNIT)


def format_growth_rate(value, decimals=3, unavailable="not available"):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return unavailable
    if abs(number) < 0.5 * (10 ** -decimals):
        number = 0.0
    return f"{number:.{decimals}f} {GROWTH_RATE_UNIT}"


def format_flux(value, decimals=3, unavailable="not available", signed=False):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return unavailable
    if abs(number) < 0.5 * (10 ** -decimals):
        number = 0.0
    spec = f"+.{decimals}f" if signed else f".{decimals}f"
    return f"{format(number, spec)} {FLUX_UNIT}"
