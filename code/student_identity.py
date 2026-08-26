
"""Student identity rules shared by gameplay and registration UI."""

MAX_STUDENT_NAME_LENGTH = 60


def normalize_student_name(value):
    """Trim/collapse whitespace while preserving Unicode names."""
    return " ".join(str(value or "").strip().split())


def validate_student_name(value):
    """Return ``(is_valid, normalized_name, error_message)``."""
    name = normalize_student_name(value)
    if len(name) < 2:
        return False, name, "Please enter your full name."
    if len(name) > MAX_STUDENT_NAME_LENGTH:
        return False, name, f"Name must have at most {MAX_STUDENT_NAME_LENGTH} characters."
    return True, name, ""


def infer_name_confirmed(player_name, missions_activated, missions_completed, player_state, default_name):
    """Preserve historic campaigns while new games require registration."""
    state = player_state if isinstance(player_state, dict) else {}
    if "name_confirmed" in state:
        return bool(state.get("name_confirmed"))
    if missions_activated or missions_completed:
        return True
    return normalize_student_name(player_name) != normalize_student_name(default_name)
