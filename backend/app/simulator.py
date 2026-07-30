from pathlib import Path

from cobra.io import read_sbml_model
from mewpy.simulation import get_simulator

from app.schemas import SimulateRequest, SimulateResponse
from app.gpr import disabled_reaction_ids

_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "e_coli_core.xml.gz"
_model = read_sbml_model(str(_MODEL_PATH))
_simul = get_simulator(_model)
_genes = _simul.find_genes()


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
            clean_fluxes[str(reaction_id)] = round(float(value), 6)
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
    return "solver_objective_value"


def simulate(req: SimulateRequest) -> SimulateResponse:
    try:
        _simul.objective = req.objective

        constraints = {k: tuple(v) for k, v in req.env_conditions.items()}

        known_knockouts = [
            gene_id for gene_id in req.gene_knockouts
            if gene_id in _genes.index
        ]
        for reaction_id in disabled_reaction_ids(_model, known_knockouts):
            constraints[reaction_id] = (0.0, 0.0)

        result = _simul.simulate(method=req.method, constraints=constraints)

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
        solver_value = _parse_solver_value(result)
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
            result=round(float(primary_objective_flux), 3),
            primary_objective_flux=round(float(primary_objective_flux), 6),
            method_score=round(float(solver_value), 6) if solver_value is not None else None,
            method_score_name=_method_score_name(req.method),
            total_absolute_flux=round(float(total_absolute_flux), 6) if total_absolute_flux is not None else None,
            active_reaction_count=active_reaction_count,
            status="ok",
            fluxes=fluxes,
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
