from typing import Literal
from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    method: Literal["FBA", "pFBA", "ROOM", "lMOMA"] = "FBA"
    objective: str = Field(
        ...,
        description="Reaction id used as the objective, e.g. BIOMASS_Ecoli_core_w_GAM",
    )
    gene_knockouts: list[str] = Field(
        default_factory=list,
        description="List of gene ids to knock out before simulating.",
    )
    env_conditions: dict[str, tuple[float, float]] = Field(
        default_factory=dict,
        description="Exchange-reaction bounds: reaction_id -> (lower_bound, upper_bound).",
    )


class SimulateResponse(BaseModel):
    objective: str
    result: float | str
    status: Literal["ok", "infeasible", "error"]
    message: str | None = None
    fluxes: dict[str, float] | None = None
    method: Literal["FBA", "pFBA", "ROOM", "lMOMA"] | None = None
    objective_reaction: str | None = None
    primary_objective_flux: float | None = None
    method_score: float | None = None
    method_score_name: str | None = None
    total_absolute_flux: float | None = None
    active_reaction_count: int | None = None
    gpr_disabled_reactions: list[str] | None = None
    reference_method: str | None = None
    reference_objective_reaction: str | None = None
    reference_primary_objective_flux: float | None = None
    reference_uses_same_environment: bool | None = None
    reference_has_no_gene_knockouts: bool | None = None
    reference_cytbd_flux: float | None = None
    room_delta: float | None = None
    room_epsilon: float | None = None
    room_linear: bool | None = None
    room_solver: str | None = None
    room_time_limit_seconds: float | None = None
