"""Student-facing wrong-answer penalty integration.

The score arithmetic lives in :mod:`hint_system`; this module owns the runtime
side effects shared by mission UIs: persist the penalty immediately and tell
the student what it cost.
"""

from functions import animation_text_save
from hint_system import MAX_MISSION_SCORE, WRONG_ANSWER_PENALTY, normalize_mission_id
from save_load import save_file


def penalize_wrong_answer(player, mission_id):
    """Charge one point for a rejected final-answer submission.

    Returns the HintSystem result when a real Player/HintSystem is available.
    Lightweight test doubles without a hint system are left untouched so older
    mission-unit tests can continue exercising UI guards independently.
    """
    mission_id = normalize_mission_id(mission_id)
    hint_system = getattr(player, 'hint_system', None)
    if hint_system is None:
        return None

    result = hint_system.record_wrong_answer(mission_id)
    if not result.get('applied'):
        return result

    # HintSystem owns the same dict, but keep Player.reward_state explicitly in
    # sync for callers/tests that inspect it directly.
    player.reward_state = hint_system.state
    save_file(player.get_save_data())

    score = int(result['current_score'])
    wrong_answers = int(result['wrong_answers'])
    score_loss = int(result.get('score_loss', 0))
    if score_loss > 0:
        message = (
            f'Incorrect final answer: -{score_loss} point. Mission {mission_id} score now '
            f'{score}/{MAX_MISSION_SCORE}. Wrong submissions: {wrong_answers}.'
        )
    else:
        message = (
            f'Incorrect final answer recorded. Mission {mission_id} score is already '
            f'{score}/{MAX_MISSION_SCORE}. Wrong submissions: {wrong_answers}.'
        )
    animation_text_save(message, time=3400)
    return result
