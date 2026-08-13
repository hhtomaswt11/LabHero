from cobra.flux_analysis import moma, pfba
from mewpy.simulation import get_simulator

from app.schemas import SimulateRequest, SimulateResponse
from app.gpr import disabled_reaction_ids
from app.model_registry import get_model_profile, load_model_template, normalise_model_id
from app.room_milp import (
    ROOM_HIGHS_SOLVER_NAME,
    ROOM_HIGHS_TIME_LIMIT_SECONDS,
    solve_integer_room_highs,
)

_DISPLAY_ZERO_TOLERANCE = 0.0005
_ROOM_DELTA = 0.03
_ROOM_EPSILON = 0.001
_ROOM_LINEAR = False


def _clean_numeric(value: float, decimals: int) -> float:
    numeric = round(float(value), decimals)
    if abs(numeric) < _DISPLAY_ZERO_TOLERANCE:
        return 0.0
    return numeric


def _extract_fluxes(result) -> dict[str, float] | None:
    fluxes = getattr(result, 'fluxes', None)
    if fluxes is None:
        return None
    if callable(fluxes):
        try:
            fluxes = fluxes()
        except TypeError:
            pass
    if hasattr(fluxes, 'to_dict'):
        try:
            fluxes = fluxes.to_dict()
        except Exception:
            pass
    if not isinstance(fluxes, dict):
        try:
            fluxes = dict(fluxes)
        except Exception:
            return None
    clean_fluxes = {}
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
    return {
        'pFBA': 'total_absolute_flux',
        'FBA': 'primary_objective_flux',
        'lMOMA': 'total_absolute_flux_adjustment',
        'ROOM': 'significant_flux_change_score',
    }.get(method, 'solver_objective_value')


def _apply_constraints(cobra_model, constraints: dict[str, tuple[float, float]]) -> None:
    for reaction_id, bounds in constraints.items():
        lower_bound, upper_bound = bounds
        reaction = cobra_model.reactions.get_by_id(str(reaction_id))
        reaction.bounds = (float(lower_bound), float(upper_bound))


def _simulate_lmoma_with_explicit_reference(
    template,
    objective: str,
    environmental_constraints: dict[str, tuple[float, float]],
    disabled_reactions: list[str],
):
    reference_model = template.copy()
    reference_model.objective = objective
    _apply_constraints(reference_model, environmental_constraints)
    reference_solution = reference_model.optimize()
    if str(reference_solution.status).lower() != 'optimal':
        raise RuntimeError(
            f'Could not construct the wild-type FBA reference for lMOMA: {reference_solution.status}.'
        )

    mutant_model = template.copy()
    mutant_model.objective = objective
    _apply_constraints(mutant_model, environmental_constraints)
    _apply_constraints(mutant_model, {rid: (0.0, 0.0) for rid in disabled_reactions})
    result = moma(mutant_model, solution=reference_solution, linear=True)
    if str(result.status).lower() != 'optimal':
        raise RuntimeError(f'Linear MOMA did not return an optimal solution: {result.status}.')

    reference_fluxes = _extract_fluxes(reference_solution) or {}
    metadata = {
        'reference_method': 'FBA',
        'reference_objective_reaction': objective,
        'reference_primary_objective_flux': reference_fluxes.get(objective),
        'reference_uses_same_environment': True,
        'reference_has_no_gene_knockouts': True,
    }
    return result, metadata


def _simulate_room_with_explicit_reference(
    template,
    objective: str,
    environmental_constraints: dict[str, tuple[float, float]],
    disabled_reactions: list[str],
    reference_target: str | None,
):
    reference_model = template.copy()
    reference_model.objective = objective
    _apply_constraints(reference_model, environmental_constraints)
    reference_solution = pfba(reference_model)
    if str(reference_solution.status).lower() != 'optimal':
        raise RuntimeError(
            f'Could not construct the wild-type pFBA reference for ROOM: {reference_solution.status}.'
        )

    mutant_model = template.copy()
    mutant_model.objective = objective
    _apply_constraints(mutant_model, environmental_constraints)
    _apply_constraints(mutant_model, {rid: (0.0, 0.0) for rid in disabled_reactions})
    result = solve_integer_room_highs(
        mutant_model,
        reference_solution,
        delta=_ROOM_DELTA,
        epsilon=_ROOM_EPSILON,
        time_limit_seconds=ROOM_HIGHS_TIME_LIMIT_SECONDS,
    )
    if str(result.status).lower() != 'optimal':
        raise RuntimeError(f'ROOM did not return an optimal solution: {result.status}.')

    reference_fluxes = _extract_fluxes(reference_solution) or {}
    result_fluxes = _extract_fluxes(result) or {}
    metadata = {
        'reference_method': 'pFBA',
        'reference_objective_reaction': objective,
        'reference_primary_objective_flux': reference_fluxes.get(objective),
        'reference_uses_same_environment': True,
        'reference_has_no_gene_knockouts': True,
        'room_delta': _ROOM_DELTA,
        'room_epsilon': _ROOM_EPSILON,
        'room_linear': _ROOM_LINEAR,
        'room_solver': getattr(result, 'room_solver', ROOM_HIGHS_SOLVER_NAME),
        'room_time_limit_seconds': getattr(result, 'room_time_limit_seconds', ROOM_HIGHS_TIME_LIMIT_SECONDS),
    }
    if reference_target:
        metadata.update({
            'reference_target_reaction': reference_target,
            'reference_target_flux': reference_fluxes.get(reference_target),
            'mutant_target_reaction': reference_target,
            'mutant_target_flux': result_fluxes.get(reference_target),
        })
        if reference_target == 'CYTBD':
            metadata['reference_cytbd_flux'] = reference_fluxes.get(reference_target)
    return result, metadata


def simulate(req: SimulateRequest) -> SimulateResponse:
    model_id = normalise_model_id(req.model_id)
    try:
        profile = get_model_profile(model_id)
        template = load_model_template(model_id)

        supported_methods = tuple(profile.get('supported_methods') or ())
        if supported_methods and req.method not in supported_methods:
            raise ValueError(
                f'Method {req.method} is not enabled for model {model_id}. '
                f'Supported methods: {", ".join(supported_methods)}'
            )

        # Validate model-scoped ids before running an expensive solver.
        template.reactions.get_by_id(req.objective)
        environmental_constraints = {k: tuple(v) for k, v in req.env_conditions.items()}
        for reaction_id in environmental_constraints:
            template.reactions.get_by_id(reaction_id)

        known_gene_ids = {str(gene.id) for gene in template.genes}
        requested_knockouts = [str(gene_id) for gene_id in req.gene_knockouts]
        unknown_knockouts = sorted({gene_id for gene_id in requested_knockouts if gene_id not in known_gene_ids})
        if unknown_knockouts:
            raise ValueError(
                'Unknown gene id(s) for model ' + model_id + ': ' + ', '.join(unknown_knockouts)
            )
        known_knockouts = list(dict.fromkeys(requested_knockouts))
        disabled_reactions = disabled_reaction_ids(template, known_knockouts)

        method_metadata: dict[str, object] = {}
        if req.method == "lMOMA":
            result, method_metadata = _simulate_lmoma_with_explicit_reference(
                template, req.objective, environmental_constraints, disabled_reactions,
            )
            solver_value = getattr(result, 'objective_value', None)
        elif req.method == "ROOM":
            result, method_metadata = _simulate_room_with_explicit_reference(
                template,
                req.objective,
                environmental_constraints,
                disabled_reactions,
                profile.get('room_reference_target'),
            )
            solver_value = getattr(result, 'objective_value', None)
        else:
            # Per-request model copy: no shared objective/bound mutation between users.
            working_model = template.copy()
            simul = get_simulator(working_model)
            simul.objective = req.objective
            constraints = dict(environmental_constraints)
            for reaction_id in disabled_reactions:
                constraints[reaction_id] = (0.0, 0.0)
            result = simul.simulate(method=req.method, constraints=constraints)
            solver_value = _parse_solver_value(result)

        text = str(result)
        lines = text.splitlines()
        if len(lines) > 1 and lines[1].strip() == 'Status: INFEASIBLE':
            return SimulateResponse(
                model_id=model_id,
                objective=req.objective,
                objective_reaction=req.objective,
                method=req.method,
                result='Status: INFEASIBLE',
                status='infeasible',
            )

        fluxes = _extract_fluxes(result) or {}
        primary_objective_flux = fluxes.get(req.objective)
        if primary_objective_flux is None and req.method == 'FBA':
            primary_objective_flux = solver_value
        if primary_objective_flux is None:
            raise ValueError(
                f'Solver result did not expose the primary objective-reaction flux for {req.objective}.'
            )

        total_absolute_flux = sum(abs(float(value)) for value in fluxes.values()) if fluxes else None
        active_reaction_count = (
            sum(1 for value in fluxes.values() if abs(float(value)) > 1e-7)
            if fluxes else None
        )
        return SimulateResponse(
            model_id=model_id,
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
            status='ok',
            fluxes=fluxes,
            **method_metadata,
        )

    except Exception as exc:
        error_name = type(exc).__name__.strip().lower()
        error_text = str(exc).strip().lower()
        if error_name == 'infeasible' or 'infeasible' in error_text:
            return SimulateResponse(
                model_id=model_id,
                objective=req.objective,
                objective_reaction=req.objective,
                method=req.method,
                result='Status: INFEASIBLE',
                status='infeasible',
            )
        return SimulateResponse(
            model_id=model_id,
            objective=req.objective,
            objective_reaction=req.objective,
            method=req.method,
            result=str(exc),
            status='error',
            message=str(exc),
        )
