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
                result="Status: INFEASIBLE",
                status="infeasible",
            )
        value = round(float(lines[0][11:]), 3)
        return SimulateResponse(
            objective=req.objective,
            result=value,
            status="ok",
            fluxes=_extract_fluxes(result),
        )

    except Exception as e:
        return SimulateResponse(
            objective=req.objective,
            result=str(e),
            status="error",
            message=str(e),
        )
