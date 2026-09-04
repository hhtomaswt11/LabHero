"""Teacher mission-jump support for isolated LabHero previews.

Teacher previews deliberately reuse the student's canonical mission numbers.
Normal previews reproduce the full 40-mission predecessor chain; Easy previews
reproduce only the curated Easy predecessors.  The preview itself is isolated
by the save namespace selected in :mod:`LabHero`, so normal student progress is
never loaded or overwritten.

Web fallbacks remain available through the server-protected route::

    /teacher/?mission=25&mode=easy

Desktop automation remains available through CLI flags::

    python3 LabHero.py --teacher --mission 25 --mode easy

The user-friendly in-game entry point is hidden on the title screen behind
SHIFT+T and authenticates server-side before constructing the same request.
"""

import sys
from urllib.parse import parse_qs

from campaign import EASY_MISSIONS, NORMAL_MISSIONS, normalize_mission_id
from hint_system import create_reward_state, initial_keys_for_campaign


TEACHER_DISPLAY_NAME = "Teacher Preview"
TEACHER_CAMPAIGN_MODES = ("normal", "easy")


def normalize_teacher_campaign_mode(mode, default="normal"):
    value = str(mode or default).strip().lower()
    return value if value in TEACHER_CAMPAIGN_MODES else default


def teacher_missions_for_mode(campaign_mode="normal"):
    mode = normalize_teacher_campaign_mode(campaign_mode)
    return EASY_MISSIONS if mode == "easy" else NORMAL_MISSIONS


def validate_teacher_mission(mission_id, campaign_mode="normal"):
    mission_id = normalize_mission_id(mission_id)
    sequence = teacher_missions_for_mode(campaign_mode)
    return mission_id if mission_id in sequence else None


def build_teacher_request(mission_id, campaign_mode="normal", source="title"):
    mode = normalize_teacher_campaign_mode(campaign_mode)
    target = validate_teacher_mission(mission_id, mode)
    if target is None:
        return None
    return {
        "mission_id": target,
        "campaign_mode": mode,
        "source": str(source or "title"),
    }


def parse_teacher_query(search):
    """Parse mission + route inside the already-authorised teacher URL."""
    query = str(search or "").strip()
    if query.startswith("?"):
        query = query[1:]
    values = parse_qs(query, keep_blank_values=True)
    mode = normalize_teacher_campaign_mode((values.get("mode") or ["normal"])[0])
    return build_teacher_request(
        (values.get("mission") or [None])[0],
        mode,
        source="web",
    )


def is_teacher_web_path(pathname):
    """Return True only for the server-protected /teacher/ namespace.

    The public root must never activate Teacher Preview from query parameters
    alone. Production nginx protects /teacher/ with HTTP Basic Auth before the
    Pygbag entry document is served.
    """
    path = str(pathname or "").strip()
    return path == "/teacher" or path.startswith("/teacher/")


def parse_teacher_web_request(pathname, search):
    if not is_teacher_web_path(pathname):
        return None
    return parse_teacher_query(search)


def parse_teacher_argv(argv):
    args = [str(value) for value in (argv or [])]
    if "--teacher" not in args:
        return None

    mission_value = None
    mode_value = "normal"
    for index, arg in enumerate(args):
        if arg.startswith("--mission="):
            mission_value = arg.split("=", 1)[1]
        elif arg == "--mission" and index + 1 < len(args):
            mission_value = args[index + 1]
        elif arg.startswith("--mode="):
            mode_value = arg.split("=", 1)[1]
        elif arg == "--mode" and index + 1 < len(args):
            mode_value = args[index + 1]

    mode = normalize_teacher_campaign_mode(mode_value)
    return build_teacher_request(mission_value, mode, source="desktop")


def get_teacher_request():
    if sys.platform == "emscripten":
        try:
            from platform import window
            request = parse_teacher_web_request(
                str(window.location.pathname),
                str(window.location.search),
            )
            if request is not None:
                return request
        except Exception:
            return None
        return None
    return parse_teacher_argv(sys.argv[1:])


def previous_teacher_missions(target_mission, campaign_mode="normal"):
    mode = normalize_teacher_campaign_mode(campaign_mode)
    target = validate_teacher_mission(target_mission, mode)
    if target is None:
        raise ValueError(
            f"Invalid {mode} teacher mission: {target_mission}"
        )
    sequence = teacher_missions_for_mode(mode)
    index = sequence.index(target)
    return sequence[:index]


def build_teacher_save_data(target_mission, campaign_mode="normal"):
    """Return an isolated six-field save payload for one teacher preview.

    Only predecessors in the selected route are marked complete.  Therefore an
    Easy preview of Mission 25 contains M01/M03/.../M23, not fake completions of
    Normal-only missions.  Canonical mission ids remain unchanged.
    """
    mode = normalize_teacher_campaign_mode(campaign_mode)
    target = validate_teacher_mission(target_mission, mode)
    if target is None:
        raise ValueError(
            f"Invalid {mode} teacher mission: {target_mission}"
        )

    previous = previous_teacher_missions(target, mode)
    # Runtime mission lists are historically newest-first. Membership is what
    # progression relies on, but preserving that convention keeps mission/NPC
    # code consistent with normal saves.
    completed = list(reversed(previous))
    activated = list(completed)

    player_state = {
        "scene": "main_map",
        "x": None,
        "y": None,
        "facing": "down",
        "status": "down_idle",
        "skin_id": "default",
        "name_confirmed": True,
        "campaign_mode": mode,
        # Student final-results summaries are irrelevant in a teacher preview.
        "final_results_seen": True,
    }

    reward_state = create_reward_state(legacy_completed=completed)
    reward_state["keys"] = initial_keys_for_campaign(mode)

    return [
        TEACHER_DISPLAY_NAME,
        [],
        activated,
        completed,
        player_state,
        reward_state,
    ]
