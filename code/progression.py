"""Central progression rules for rewards unlocked by mission completion.

The rules in this module are deliberately data-only and do not import pygame.
That keeps them reusable by the current desktop game, the future browser UI,
and later map-gating/door code without duplicating mission-number checks.
"""

UNLOCK_RULES = {
    'skin:golden': '35',
    'area:golden_lab': '35',
    'model:yeast_iMM904': '35',
}


def _completed_set(missions_completed):
    return {str(value) for value in (missions_completed or [])}


def unlock_requirement(kind, item_id):
    """Return the mission id required for an unlock, or ``None`` if unrestricted."""
    return UNLOCK_RULES.get(f'{kind}:{item_id}')


def mission_requirement_met(required_mission, missions_completed, campaign_context=None):
    if not required_mission:
        return True
    if campaign_context is not None:
        return campaign_context.is_progression_requirement_met(
            required_mission, missions_completed
        )
    return str(required_mission) in _completed_set(missions_completed)


def is_unlock_available(kind, item_id, missions_completed, campaign_context=None):
    return mission_requirement_met(
        unlock_requirement(kind, item_id),
        missions_completed,
        campaign_context=campaign_context,
    )


def is_skin_unlocked(skin_id, missions_completed):
    return is_unlock_available('skin', skin_id, missions_completed)


def is_area_unlocked(area_id, missions_completed):
    return is_unlock_available('area', area_id, missions_completed)


def is_model_unlocked(model_id, missions_completed, campaign_context=None):
    return is_unlock_available(
        'model', model_id, missions_completed,
        campaign_context=campaign_context,
    )


def mission35_reward_state(missions_completed):
    """JSON-serialisable reward state derived only from mission completion."""
    return {
        'golden_skin_unlocked': is_skin_unlocked('golden', missions_completed),
        'golden_lab_unlocked': is_area_unlocked('golden_lab', missions_completed),
        'yeast_simulator_unlocked': is_model_unlocked('yeast_iMM904', missions_completed),
    }
