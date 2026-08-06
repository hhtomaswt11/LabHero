"""Deterministic integer ROOM solver backed by SciPy/HiGHS.

COBRApy's standard ROOM formulation is mathematically correct, but its default
GLPK MILP backend can take an unbounded amount of wall time on the aerobic
E. coli cut-set used by Mission 33.  This module implements the same binary ROOM
formulation with SciPy's HiGHS MILP solver and an explicit safety time limit.

The helper is deliberately independent of Mission 33: it accepts any COBRApy
model and a complete reference flux solution, so it can later be reused by the
web service and by other metabolic models.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any


ROOM_HIGHS_SOLVER_NAME = "scipy-highs-milp"
ROOM_HIGHS_TIME_LIMIT_SECONDS = 12.0
ROOM_HIGHS_INTEGER_TOLERANCE = 1e-6
ROOM_HIGHS_ZERO_TOLERANCE = 1e-9


def _reference_flux_mapping(reference_solution: Any) -> dict[str, float]:
    fluxes = getattr(reference_solution, "fluxes", None)
    if callable(fluxes):
        try:
            fluxes = fluxes()
        except TypeError:
            pass
    if hasattr(fluxes, "to_dict"):
        fluxes = fluxes.to_dict()
    if not isinstance(fluxes, dict):
        try:
            fluxes = dict(fluxes)
        except Exception as exc:
            raise RuntimeError("ROOM reference did not expose a complete flux mapping.") from exc

    clean: dict[str, float] = {}
    for reaction_id, value in fluxes.items():
        try:
            clean[str(reaction_id)] = float(value)
        except (TypeError, ValueError):
            continue
    return clean


def solve_integer_room_highs(
    cobra_model: Any,
    reference_solution: Any,
    *,
    delta: float = 0.03,
    epsilon: float = 0.001,
    time_limit_seconds: float = ROOM_HIGHS_TIME_LIMIT_SECONDS,
) -> SimpleNamespace:
    """Solve the standard integer ROOM formulation with HiGHS.

    Variables are the mutant reaction fluxes ``v`` and one binary indicator
    ``y`` per reaction.  The objective minimises ``sum(y)`` subject to steady
    state, reaction bounds and the standard ROOM upper/lower tolerance bands.

    A lightweight COBRA-like result is returned with ``status``,
    ``objective_value`` and a full ``fluxes`` mapping.  The caller therefore
    consumes it exactly like the result returned by ``cobra.flux_analysis.room``.
    """
    try:
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import csc_matrix, diags, eye, hstack, vstack
    except Exception as exc:
        raise RuntimeError(
            "Integer ROOM requires SciPy with scipy.optimize.milp support."
        ) from exc

    reactions = list(cobra_model.reactions)
    metabolites = list(cobra_model.metabolites)
    if not reactions or not metabolites:
        raise RuntimeError("ROOM cannot solve an empty metabolic model.")

    reaction_count = len(reactions)
    metabolite_index = {metabolite.id: index for index, metabolite in enumerate(metabolites)}

    row_indices: list[int] = []
    column_indices: list[int] = []
    coefficients: list[float] = []
    lower_bounds = np.empty(reaction_count, dtype=float)
    upper_bounds = np.empty(reaction_count, dtype=float)

    for column, reaction in enumerate(reactions):
        lower_bounds[column] = float(reaction.lower_bound)
        upper_bounds[column] = float(reaction.upper_bound)
        for metabolite, coefficient in reaction.metabolites.items():
            row_indices.append(metabolite_index[metabolite.id])
            column_indices.append(column)
            coefficients.append(float(coefficient))

    if not np.all(np.isfinite(lower_bounds)) or not np.all(np.isfinite(upper_bounds)):
        raise RuntimeError("ROOM requires finite reaction bounds.")
    if np.any(lower_bounds > upper_bounds):
        raise RuntimeError("ROOM received inconsistent reaction bounds.")

    reference_fluxes = _reference_flux_mapping(reference_solution)
    missing_reference_fluxes = [reaction.id for reaction in reactions if reaction.id not in reference_fluxes]
    if missing_reference_fluxes:
        preview = ", ".join(missing_reference_fluxes[:5])
        raise RuntimeError(f"ROOM reference is missing reaction fluxes: {preview}.")

    reference = np.array([reference_fluxes[reaction.id] for reaction in reactions], dtype=float)
    if not np.all(np.isfinite(reference)):
        raise RuntimeError("ROOM reference contains non-finite flux values.")

    stoichiometry = csc_matrix(
        (coefficients, (row_indices, column_indices)),
        shape=(len(metabolites), reaction_count),
        dtype=float,
    )
    zero_block = csc_matrix((len(metabolites), reaction_count), dtype=float)
    steady_state = hstack([stoichiometry, zero_block], format="csc")

    upper_tolerance = reference + float(delta) * np.abs(reference) + float(epsilon)
    lower_tolerance = reference - float(delta) * np.abs(reference) - float(epsilon)

    identity = eye(reaction_count, format="csc", dtype=float)
    room_upper = hstack(
        [identity, -diags(upper_bounds - upper_tolerance, format="csc")],
        format="csc",
    )
    room_lower = hstack(
        [-identity, diags(lower_bounds - lower_tolerance, format="csc")],
        format="csc",
    )
    constraint_matrix = vstack([steady_state, room_upper, room_lower], format="csc")

    metabolite_count = len(metabolites)
    constraint_lower = np.concatenate([
        np.zeros(metabolite_count, dtype=float),
        np.full(2 * reaction_count, -np.inf, dtype=float),
    ])
    constraint_upper = np.concatenate([
        np.zeros(metabolite_count, dtype=float),
        upper_tolerance,
        -lower_tolerance,
    ])

    objective = np.concatenate([
        np.zeros(reaction_count, dtype=float),
        np.ones(reaction_count, dtype=float),
    ])
    integrality = np.concatenate([
        np.zeros(reaction_count, dtype=int),
        np.ones(reaction_count, dtype=int),
    ])
    variable_lower = np.concatenate([
        lower_bounds,
        np.zeros(reaction_count, dtype=float),
    ])
    variable_upper = np.concatenate([
        upper_bounds,
        np.ones(reaction_count, dtype=float),
    ])

    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(variable_lower, variable_upper),
        constraints=LinearConstraint(
            constraint_matrix,
            constraint_lower,
            constraint_upper,
        ),
        options={
            "disp": False,
            "presolve": True,
            "time_limit": float(time_limit_seconds),
            "mip_rel_gap": 0.0,
        },
    )

    if not bool(getattr(result, "success", False)) or getattr(result, "x", None) is None:
        message = str(getattr(result, "message", "unknown HiGHS failure"))
        raise RuntimeError(
            "Integer ROOM could not prove an optimal solution within the "
            f"{float(time_limit_seconds):g}-second safety limit: {message}"
        )

    raw_score = float(result.fun)
    rounded_score = round(raw_score)
    if abs(raw_score - rounded_score) > ROOM_HIGHS_INTEGER_TOLERANCE:
        raise RuntimeError(
            f"Integer ROOM returned a non-integer significant-change score: {raw_score}."
        )

    mutant_fluxes: dict[str, float] = {}
    for index, reaction in enumerate(reactions):
        value = float(result.x[index])
        if abs(value) < ROOM_HIGHS_ZERO_TOLERANCE:
            value = 0.0
        mutant_fluxes[reaction.id] = value

    return SimpleNamespace(
        status="optimal",
        objective_value=float(rounded_score),
        fluxes=mutant_fluxes,
        room_solver=ROOM_HIGHS_SOLVER_NAME,
        room_time_limit_seconds=float(time_limit_seconds),
        room_mip_gap=float(getattr(result, "mip_gap", 0.0) or 0.0),
        room_mip_node_count=int(getattr(result, "mip_node_count", 0) or 0),
    )
