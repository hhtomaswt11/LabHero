"""Central campaign/progression rules for map gates and future modes."""

VALID_CAMPAIGN_MODES = ("normal", "easy", "teacher")


def normalize_mission_id(mission_id):
    if mission_id is None:
        return None
    value = str(mission_id).strip()
    if not value:
        return None
    if value.lower().startswith("mission"):
        value = value[7:].strip()
    try:
        return f"{int(value):02d}"
    except (TypeError, ValueError):
        return value


class CampaignContext:
    """Progression policy used by physical map gates.

    Easy mode is not implemented yet, so it currently follows Normal rules.
    Teacher mode is reserved now and bypasses physical progression gates.
    """

    def __init__(self, mode="normal"):
        mode = str(mode or "normal").strip().lower()
        if mode not in VALID_CAMPAIGN_MODES:
            raise ValueError(f"Unsupported campaign mode: {mode}")
        self.mode = mode

    def is_mission_effectively_completed(self, mission_id, missions_completed):
        target = normalize_mission_id(mission_id)
        completed = {normalize_mission_id(item) for item in (missions_completed or [])}
        return target in completed

    def should_gate_be_open(self, required_mission, missions_completed):
        if self.mode == "teacher":
            return True
        return self.is_mission_effectively_completed(required_mission, missions_completed)
