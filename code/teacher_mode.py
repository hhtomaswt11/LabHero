"""Teacher mission-jump support for isolated LabHero previews.

Web (production):
    /teacher/?mission=17
    The /teacher/ route must be protected by the deployment web server.

Desktop:
    python3 LabHero.py --teacher --mission 17

The teacher session uses a separate persistence namespace and an ephemeral
campaign state in which missions before the target are completed. The student's
normal save is never loaded or overwritten.
"""

import sys
from urllib.parse import parse_qs

from campaign import NORMAL_MISSIONS, normalize_mission_id
from hint_system import create_reward_state


TEACHER_DISPLAY_NAME = "Teacher Preview"


def validate_teacher_mission(mission_id):
    mission_id = normalize_mission_id(mission_id)
    return mission_id if mission_id in NORMAL_MISSIONS else None


def parse_teacher_query(search):
    """Parse only the mission selector used inside an authorised teacher route."""
    query = str(search or "").strip()
    if query.startswith("?"):
        query = query[1:]
    values = parse_qs(query, keep_blank_values=True)
    mission_id = validate_teacher_mission((values.get("mission") or [None])[0])
    if mission_id is None:
        return None
    return {"mission_id": mission_id, "source": "web"}


def is_teacher_web_path(pathname):
    """Return True only for the server-protected /teacher/ namespace.

    The public root must never activate Teacher Mode from query parameters
    alone.  Production nginx protects /teacher/ with HTTP Basic Auth before
    the Pygbag bundle is served.
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
    for index, arg in enumerate(args):
        if arg.startswith("--mission="):
            mission_value = arg.split("=", 1)[1]
            break
        if arg == "--mission" and index + 1 < len(args):
            mission_value = args[index + 1]
            break

    mission_id = validate_teacher_mission(mission_value)
    if mission_id is None:
        return None
    return {"mission_id": mission_id, "source": "desktop"}


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


def previous_teacher_missions(target_mission):
    target = validate_teacher_mission(target_mission)
    if target is None:
        raise ValueError(f"Invalid teacher mission: {target_mission}")
    index = NORMAL_MISSIONS.index(target)
    return NORMAL_MISSIONS[:index]


def build_teacher_save_data(target_mission):
    """Return an isolated six-field save payload for one teacher preview."""
    target = validate_teacher_mission(target_mission)
    if target is None:
        raise ValueError(f"Invalid teacher mission: {target_mission}")

    previous = previous_teacher_missions(target)
    # Runtime mission lists are historically newest-first. Membership is what
    # progression relies on, but keeping that convention also preserves NPC
    # chain behaviour for direct teacher previews.
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
        "campaign_mode": "teacher",
        # Student final-results summaries are irrelevant in a teacher preview.
        "final_results_seen": True,
    }

    return [
        TEACHER_DISPLAY_NAME,
        [],
        activated,
        completed,
        player_state,
        create_reward_state(legacy_completed=completed),
    ]
