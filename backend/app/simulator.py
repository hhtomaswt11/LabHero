from pathlib import Path

from cobra.flux_analysis import moma, pfba
from cobra.io import read_sbml_model
from mewpy.simulation import get_simulator

from app.schemas import SimulateRequest, SimulateResponse
from app.gpr import disabled_reaction_ids
from app.room_milp import (
    ROOM_HIGHS_SOLVER_NAME,
    ROOM_HIGHS_TIME_LIMIT_SECONDS,
    solve_integer_room_highs,
)

_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "e_coli_core.xml.gz"
_model = read_sbml_model(str(_MODEL_PATH))
_simul = get_simulator(_model)
_genes = _simul.find_genes()
_DISPLAY_ZERO_TOLERANCE = 0.0005
_ROOM_DELTA = 0.03
_ROOM_EPSILON = 0.001
_ROOM_LINEAR = False
_ROOM_REFERENCE_REACTION = "CYTBD"


def _clean_numeric(value: float, decimals: int) -> float:
    """Round API numbers and avoid exposing negative zero to the browser."""
    numeric = round(float(value), decimals)
    if abs(numeric) < _DISPLAY_ZERO_TOLERANCE:
        return 0.0
    return numeric


def _extract_fluxes(result) -> dict[str, float] | None:
    fluxes = getattr(result, "fluxes", None)
    if fluxes is None:
        return None

    if callable(fluxes):
        try:
            fluxes = fluxes()
        except TypeError:
            pass

    if hasattr(fluxes, "to_dict"):
        try:
            fluxes = fluxes.to_dict()
        except Exception:
            pass

    if not isinstance(fluxes, dict):
        try:
            fluxes = dict(fluxes)
        except Exception:
            return None

    clean_fluxes: dict[str, float] = {}
    for reaction_id, value in fluxes.items():
        try:
            clean_fluxes[str(reaction_id)] = _clean_numeric(value, 6)
        except Exception:
            continue
    return clean_fluxes


def _parse_solver_value(result) -> float | None:
    try:
        return float(str(result).splitlines()[0][11:])
    except Exception:
        return None


def _method_score_name(method: str) -> str:
    if method == "pFBA":
        return "total_absolute_flux"
    if method == "FBA":
        return "primary_objective_flux"
    if method == "lMOMA":
        return "total_absolute_flux_adjustment"
    if method == "ROOM":
        return "significant_flux_change_score"
    return "solver_objective_value"


def _apply_constraints(cobra_model, constraints: dict[str, tuple[float, float]]) -> None:
    """Apply request bounds to an isolated COBRApy model copy."""
    for reaction_id, bounds in constraints.items():
        lower_bound, upper_bound = bounds
        reaction = cobra_model.reactions.get_by_id(str(reaction_id))
        reaction.bounds = (float(lower_bound), float(upper_bound))


def _simulate_lmoma_with_explicit_reference(
    objective: str,
    environmental_constraints: dict[str, tuple[float, float]],
    disabled_reactions: list[str],
):
    """Run lMOMA against a wild-type FBA reference in the same medium.

    Passing no reference to COBRApy after knockout bounds are applied makes its
    fallback pFBA solution a mutant reference and collapses the adjustment score
    to zero.  Both model copies here are independent of the shared MEWpy
    simulator: the reference has no gene knockouts, while the mutant receives
    the GPR-derived reaction closures.
    """
    reference_model = _model.copy()
    reference_model.objective = objective
    _apply_constraints(reference_model, environmental_constraints)
    reference_solution = reference_model.optimize()
    if str(reference_solution.status).lower() != "optimal":
        raise RuntimeError(
            f"Could not construct the wild-type FBA reference for lMOMA: {reference_solution.status}."
        )

    mutant_model = _model.copy()
    mutant_model.objective = objective
    _apply_constraints(mutant_model, environmental_constraints)
    _apply_constraints(
        mutant_model,
        {reaction_id: (0.0, 0.0) for reaction_id in disabled_reactions},
    )
    result = moma(mutant_model, solution=reference_solution, linear=True)
    if str(result.status).lower() != "optimal":
        raise RuntimeError(f"Linear MOMA did not return an optimal solution: {result.status}.")
    return result


def _simulate_room_with_explicit_reference(
    objective: str,
    environmental_constraints: dict[str, tuple[float, float]],
    disabled_reactions: list[str],
):
    """Run integer ROOM against a wild-type pFBA reference in the same medium.

    ROOM is a reference-state method.  Calling it after knockout constraints
    have already been applied and without an explicit solution lets the solver
    build a mutant reference, which can collapse the adjustment score to zero.
    The reference and mutant therefore use separate model copies: the same
    objective and environmental bounds, but GPR-derived reaction closures only
    on the mutant.
    """
    reference_model = _model.copy()
    reference_model.objective = objective
    _apply_constraints(reference_model, environmental_constraints)
    reference_solution = pfba(reference_model)
    if str(reference_solution.status).lower() != "optimal":
        raise RuntimeError(
            f"Could not construct the wild-type pFBA reference for ROOM: {reference_solution.status}."
        )

    mutant_model = _model.copy()
    mutant_model.objective = objective
    _apply_constraints(mutant_model, environmental_constraints)
    _apply_constraints(
        mutant_model,
        {reaction_id: (0.0, 0.0) for reaction_id in disabled_reactions},
    )
    result = solve_integer_room_highs(
        mutant_model,
        reference_solution,
        delta=_ROOM_DELTA,
        epsilon=_ROOM_EPSILON,
        time_limit_seconds=ROOM_HIGHS_TIME_LIMIT_SECONDS,
    )
    if str(result.status).lower() != "optimal":
        raise RuntimeError(f"ROOM did not return an optimal solution: {result.status}.")

    reference_fluxes = _extract_fluxes(reference_solution) or {}
    metadata = {
        "reference_method": "pFBA",
        "reference_objective_reaction": objective,
        "reference_primary_objective_flux": reference_fluxes.get(objective),
        "reference_uses_same_environment": True,
        "reference_has_no_gene_knockouts": True,
        "reference_cytbd_flux": reference_fluxes.get(_ROOM_REFERENCE_REACTION),
        "room_delta": _ROOM_DELTA,
        "room_epsilon": _ROOM_EPSILON,
        "room_linear": _ROOM_LINEAR,
        "room_solver": getattr(result, "room_solver", ROOM_HIGHS_SOLVER_NAME),
        "room_time_limit_seconds": getattr(
            result, "room_time_limit_seconds", ROOM_HIGHS_TIME_LIMIT_SECONDS
        ),
    }
    return result, metadata


def simulate(req: SimulateRequest) -> SimulateResponse:
    try:
        environmental_constraints = {k: tuple(v) for k, v in req.env_conditions.items()}

        known_knockouts = [
            gene_id for gene_id in req.gene_knockouts
            if gene_id in _genes.index
        ]
        disabled_reactions = disabled_reaction_ids(_model, known_knockouts)

        method_metadata: dict[str, object] = {}
        if req.method == "lMOMA":
            result = _simulate_lmoma_with_explicit_reference(
                req.objective,
                environmental_constraints,
                disabled_reactions,
            )
            solver_value = getattr(result, "objective_value", None)
        elif req.method == "ROOM":
            result, method_metadata = _simulate_room_with_explicit_reference(
                req.objective,
                environmental_constraints,
                disabled_reactions,
            )
            solver_value = getattr(result, "objective_value", None)
        else:
            _simul.objective = req.objective
            constraints = dict(environmental_constraints)
            for reaction_id in disabled_reactions:
                constraints[reaction_id] = (0.0, 0.0)
            result = _simul.simulate(method=req.method, constraints=constraints)
            solver_value = _parse_solver_value(result)

        text = str(result)
        lines = text.splitlines()
        if len(lines) > 1 and lines[1].strip() == "Status: INFEASIBLE":
            return SimulateResponse(
                objective=req.objective,
                objective_reaction=req.objective,
                method=req.method,
                result="Status: INFEASIBLE",
                status="infeasible",
            )

        fluxes = _extract_fluxes(result) or {}
        primary_objective_flux = fluxes.get(req.objective)
        if primary_objective_flux is None and req.method == "FBA":
            primary_objective_flux = solver_value
        if primary_objective_flux is None:
            raise ValueError(
                f"Solver result did not expose the primary objective-reaction flux for {req.objective}."
            )

        total_absolute_flux = sum(abs(float(value)) for value in fluxes.values()) if fluxes else None
        active_reaction_count = (
            sum(1 for value in fluxes.values() if abs(float(value)) > 1e-7)
            if fluxes else None
        )
        return SimulateResponse(
            objective=req.objective,
            objective_reaction=req.objective,
            method=req.method,
            result=_clean_numeric(primary_objective_flux, 3),
            primary_objective_flux=_clean_numeric(primary_objective_flux, 6),
            method_score=_clean_numeric(solver_value, 6) if solver_value is not None else None,
            method_score_name=_method_score_name(req.method),
            total_absolute_flux=_clean_numeric(total_absolute_flux, 6) if total_absolute_flux is not None else None,
            active_reaction_count=active_reaction_count,
            gpr_disabled_reactions=sorted(disabled_reactions),
            status="ok",
            fluxes=fluxes,
            **method_metadata,
        )

    except Exception as e:
        # COBRA pFBA raises ``Infeasible`` while ordinary FBA may return an
        # infeasible result object.  Expose both paths through the same API
        # contract so the browser never receives a generic backend error for a
        # scientifically meaningful infeasible model.
        error_name = type(e).__name__.strip().lower()
        error_text = str(e).strip().lower()
        if error_name == "infeasible" or "infeasible" in error_text:
            return SimulateResponse(
                objective=req.objective,
                objective_reaction=req.objective,
                method=req.method,
                result="Status: INFEASIBLE",
                status="infeasible",
            )
        return SimulateResponse(
            objective=req.objective,
            objective_reaction=req.objective,
            method=req.method,
            result=str(e),
            status="error",
            message=str(e),
        )
