"""Central campaign/progression policy for Normal, Easy and Teacher modes.

EASY.1A introduced the shared architecture, EASY.2A fixed the curated route,
and EASY.2B exposes Normal/Easy during one-time student registration while
preserving the original Normal campaign unchanged.
"""

VALID_CAMPAIGN_MODES = ("normal", "easy", "teacher")
NORMAL_MISSIONS = tuple(f"{number:02d}" for number in range(1, 41))

# EASY.2 pedagogical route (~2 h classroom version).  These are the only
# missions that count as actual Easy-mode completions; skipped Normal missions
# are never inserted into missions_completed.
EASY_MISSIONS = (
    "01", "03", "06", "07", "13", "18",
    "21", "23", "25", "27", "36",
)

MODE_MISSIONS = {
    "normal": NORMAL_MISSIONS,
    "easy": EASY_MISSIONS,
    "teacher": NORMAL_MISSIONS,
}

# Student-facing campaign modes. Teacher remains reserved for TEACHER.1 and
# is deliberately not exposed by the registration UI.
STUDENT_CAMPAIGN_MODES = ("normal", "easy")

# Tiled interaction names are historical NPC entry points, not always the same
# as the first mission number they currently launch (for example Mission02 is
# Dr. Silva's M03-M05 chain).  Easy mode maps each retained NPC directly to its
# curated mission and omits the remaining entry points entirely.
NORMAL_INTERACTION_MISSIONS = {
    "Mission01": "01", "Mission02": "03", "Mission03": "06",
    "Mission07": "07", "Mission11": "11", "Mission16": "16",
    "Mission21": "21", "Mission23": "23", "Mission25": "25",
    "Mission27": "27", "Mission29": "29", "Mission32": "32",
    "Final": "35", "Vale": "36", "Voss": "37", "Umbra": "38",
    "Morbus": "39", "Mortis": "40",
}

EASY_INTERACTION_MISSIONS = {
    "Mission01": "01",
    "Mission02": "03",
    "Mission03": "06",
    "Mission07": "07",
    "Mission11": "13",
    "Mission16": "18",
    "Mission21": "21",
    "Mission23": "23",
    "Mission25": "25",
    "Mission27": "27",
    "Vale": "36",
}

MODE_INTERACTION_MISSIONS = {
    "normal": NORMAL_INTERACTION_MISSIONS,
    "easy": EASY_INTERACTION_MISSIONS,
    "teacher": NORMAL_INTERACTION_MISSIONS,
}


# Every Normal mission belongs to one historic Tiled researcher entry point.
# TEACHER.1 uses this only as metadata; the requested mission menu itself opens
# directly, so the teacher is never forced to walk through earlier NPC chains.
TEACHER_MISSION_INTERACTIONS = {}
for _interaction_name, _first_mission in NORMAL_INTERACTION_MISSIONS.items():
    if _interaction_name == "Mission01":
        _mission_ids = range(1, 3)
    elif _interaction_name == "Mission02":
        _mission_ids = range(3, 6)
    elif _interaction_name == "Mission03":
        _mission_ids = range(6, 7)
    elif _interaction_name == "Mission07":
        _mission_ids = range(7, 11)
    elif _interaction_name == "Mission11":
        _mission_ids = range(11, 16)
    elif _interaction_name == "Mission16":
        _mission_ids = range(16, 21)
    elif _interaction_name == "Mission21":
        _mission_ids = range(21, 23)
    elif _interaction_name == "Mission23":
        _mission_ids = range(23, 25)
    elif _interaction_name == "Mission25":
        _mission_ids = range(25, 27)
    elif _interaction_name == "Mission27":
        _mission_ids = range(27, 29)
    elif _interaction_name == "Mission29":
        _mission_ids = range(29, 32)
    elif _interaction_name == "Mission32":
        _mission_ids = range(32, 35)
    else:
        _mission_ids = range(int(_first_mission), int(_first_mission) + 1)
    for _mission_number in _mission_ids:
        TEACHER_MISSION_INTERACTIONS[f"{_mission_number:02d}"] = _interaction_name


def teacher_interaction_for_mission(mission_id):
    return TEACHER_MISSION_INTERACTIONS.get(normalize_mission_id(mission_id))


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


def normalize_campaign_mode(mode, default="normal"):
    value = str(mode or default).strip().lower()
    if value not in VALID_CAMPAIGN_MODES:
        return default
    return value


class CampaignContext:
    """Single source of truth for campaign-mode progression metadata.

    Normal is the full 40-mission campaign.
    Easy is the curated classroom route selected in EASY.2.
    Teacher is reserved for TEACHER.1 and bypasses physical map gates.
    """

    def __init__(self, mode="normal"):
        mode = str(mode or "normal").strip().lower()
        if mode not in VALID_CAMPAIGN_MODES:
            raise ValueError(f"Unsupported campaign mode: {mode}")
        self.mode = mode

    @property
    def mission_sequence(self):
        sequence = MODE_MISSIONS[self.mode]
        return tuple(sequence) if sequence is not None else None

    @property
    def is_configured(self):
        return self.mission_sequence is not None

    @property
    def mission_count(self):
        sequence = self.mission_sequence
        return len(sequence) if sequence is not None else 0

    @property
    def max_score(self):
        """Maximum score using the existing 5 points per scored mission."""
        return self.mission_count * 5

    @property
    def first_mission(self):
        sequence = self.mission_sequence
        return sequence[0] if sequence else None

    @property
    def final_mission(self):
        sequence = self.mission_sequence
        return sequence[-1] if sequence else None


    def mission_for_interaction(self, interaction_name):
        """Return the mission represented by a Tiled NPC entry point in this mode.

        ``None`` means that researcher/entry point is intentionally outside the
        current student route.  This prevents skipped Easy missions from being
        exposed through the historic multi-mission NPC chains.
        """
        mapping = MODE_INTERACTION_MISSIONS[self.mode]
        return mapping.get(str(interaction_name or ""))

    def interaction_is_available(self, interaction_name):
        return self.mission_for_interaction(interaction_name) is not None

    def includes_mission(self, mission_id):
        sequence = self.mission_sequence
        if sequence is None:
            return False
        return normalize_mission_id(mission_id) in sequence

    def previous_mission(self, mission_id):
        """Return the previous mission in this mode's sequence, if any."""
        sequence = self.mission_sequence
        if sequence is None:
            return None
        target = normalize_mission_id(mission_id)
        try:
            index = sequence.index(target)
        except ValueError:
            return None
        return sequence[index - 1] if index > 0 else None

    def next_mission(self, mission_id):
        """Return the next mission in this mode's sequence, if any."""
        sequence = self.mission_sequence
        if sequence is None:
            return None
        target = normalize_mission_id(mission_id)
        try:
            index = sequence.index(target)
        except ValueError:
            return None
        next_index = index + 1
        return sequence[next_index] if next_index < len(sequence) else None

    def mission_requirement(self, mission_id):
        """Return the actual previous mission required by this campaign mode.

        A mission omitted from the current mode has no progression requirement
        because it is not playable in that mode.
        """
        target = normalize_mission_id(mission_id)
        if not self.includes_mission(target):
            return None
        return self.previous_mission(target)

    def is_mission_unlocked(self, mission_id, missions_completed):
        """Whether ``mission_id`` may be played in this campaign mode.

        Easy therefore follows its curated predecessor chain without ever
        pretending that skipped Normal missions were completed.
        """
        target = normalize_mission_id(mission_id)
        if self.mode == "teacher":
            return self.includes_mission(target)
        if not self.includes_mission(target):
            return False
        required = self.mission_requirement(target)
        if required is None:
            return True
        return self.is_mission_effectively_completed(required, missions_completed)

    def progression_milestone_for(self, required_mission):
        """Translate a legacy numeric milestone to this mode's real milestone.

        Tiled gates and historic unlock rules are intentionally left labelled
        with their Normal milestones (for example 35).  In Easy, a skipped
        milestone resolves to the last curated mission at or before it.  This
        opens the Golden Lab after M27 without adding fake M28-M35 completions.
        """
        target = normalize_mission_id(required_mission)
        if target is None or self.mode != "easy":
            return target
        sequence = self.mission_sequence or ()
        try:
            target_number = int(target)
        except ValueError:
            return target if target in sequence else None
        eligible = [
            mission_id for mission_id in sequence
            if mission_id.isdigit() and int(mission_id) <= target_number
        ]
        return eligible[-1] if eligible else None

    def is_progression_requirement_met(self, required_mission, missions_completed):
        if self.mode == "teacher":
            return True
        milestone = self.progression_milestone_for(required_mission)
        if milestone is None:
            return False
        return self.is_mission_effectively_completed(milestone, missions_completed)

    def is_mission_effectively_completed(self, mission_id, missions_completed):
        """Check actual completion only; skipped Easy missions stay incomplete."""
        target = normalize_mission_id(mission_id)
        completed = {normalize_mission_id(item) for item in (missions_completed or [])}
        return target in completed

    def completed_missions_in_mode(self, missions_completed):
        sequence = self.mission_sequence
        if sequence is None:
            return ()
        completed = {normalize_mission_id(item) for item in (missions_completed or [])}
        return tuple(mission_id for mission_id in sequence if mission_id in completed)

    def is_campaign_complete(self, missions_completed):
        final_mission = self.final_mission
        return bool(final_mission) and self.is_mission_effectively_completed(
            final_mission, missions_completed
        )

    def should_gate_be_open(self, required_mission, missions_completed):
        return self.is_progression_requirement_met(
            required_mission, missions_completed
        )
