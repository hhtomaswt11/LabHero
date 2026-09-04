"""Central key, hint and mission-score state for LabHero.

This module deliberately has no pygame dependency.  Mission UIs should ask the
HintSystem for permission to reveal a hint instead of modifying key counters
directly.  The same state is serialized as the sixth field of the main save.
"""

from copy import deepcopy


REWARD_STATE_VERSION = 2

# Normal remains the historic/full-campaign budget.  Easy deliberately starts
# with fewer keys because its curated route contains only 11 missions.  Keeping
# these values in the reward module (rather than scattering literals through
# UI code) makes registration, Alves' dialogue and tests share one source of
# truth.
CAMPAIGN_INITIAL_KEYS = {
    'normal': {
        'bronze': 15,
        'silver': 10,
        'gold': 5,
    },
    'easy': {
        'bronze': 8,
        'silver': 5,
        'gold': 2,
    },
}

# Backwards-compatible alias used by legacy-save normalization and older tests.
# Historic saves without a campaign-specific budget are Normal campaigns.
INITIAL_KEYS = dict(CAMPAIGN_INITIAL_KEYS['normal'])

# The easter egg remains a stronger reward in the full campaign.  Easy still
# rewards exploration, but one Gold Key is proportionate to its shorter route.
GOLDEN_EGG_GOLD_REWARD_BY_CAMPAIGN = {
    'normal': 3,
    'easy': 1,
}

SCORE_BY_HINT_LEVEL = {
    0: 5,
    1: 3,
    2: 2,
    3: 1,
}

# Wrong final-answer submissions are cumulative with hint penalties. A mission
# may therefore finish at 0 points, but never below 0.
MIN_MISSION_SCORE = 0
MAX_MISSION_SCORE = SCORE_BY_HINT_LEVEL[0]
WRONG_ANSWER_PENALTY = 1

KEY_FOR_HINT_LEVEL = {
    1: 'bronze',
    2: 'silver',
    3: 'gold',
}

# A stronger key may replace a weaker one, never the reverse.
KEY_CANDIDATES_BY_HINT_LEVEL = {
    1: ('bronze', 'silver', 'gold'),
    2: ('silver', 'gold'),
    3: ('gold',),
}

KEY_TYPES = tuple(INITIAL_KEYS)
VALID_HINT_LEVELS = tuple(SCORE_BY_HINT_LEVEL)

# All 40 mission UIs are now integrated with HintSystem. Historical saves
# still keep any pre-integration completions in legacy_unscored_missions, while
# new/current mission completions receive their frozen score from hint usage.
TRACKED_HINT_MISSIONS = frozenset(f'{mission:02d}' for mission in range(1, 41))


def initial_keys_for_campaign(campaign_mode):
    """Return a fresh key-budget dictionary for a student campaign mode.

    Unknown/legacy modes deliberately fall back to Normal so old save/tooling
    paths keep the historic 15/10/5 behaviour rather than unexpectedly losing
    keys.
    """
    mode = str(campaign_mode or 'normal').strip().lower()
    return dict(CAMPAIGN_INITIAL_KEYS.get(mode, CAMPAIGN_INITIAL_KEYS['normal']))


def golden_egg_gold_reward_for_campaign(campaign_mode):
    """Return the one-time Gold-Key reward for the selected campaign."""
    mode = str(campaign_mode or 'normal').strip().lower()
    return int(GOLDEN_EGG_GOLD_REWARD_BY_CAMPAIGN.get(mode, 3))


def normalize_mission_id(mission_id):
    """Return the canonical mission id used by the existing save (01..40)."""
    if isinstance(mission_id, bool):
        raise ValueError('mission_id must identify a mission')

    value = str(mission_id).strip()
    if not value:
        raise ValueError('mission_id must identify a mission')

    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError('mission_id must be a positive integer') from None

    if number <= 0:
        raise ValueError('mission_id must be a positive integer')

    return f'{number:02d}' if number < 100 else str(number)


def _safe_key_count(value, default):
    if isinstance(value, bool):
        return default
    try:
        count = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, count)


def _safe_hint_level(value):
    if isinstance(value, bool):
        return None
    try:
        level = int(value)
    except (TypeError, ValueError):
        return None
    return level if level in VALID_HINT_LEVELS else None


def _safe_score(value):
    if isinstance(value, bool):
        return None
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return score if MIN_MISSION_SCORE <= score <= MAX_MISSION_SCORE else None


def _safe_legacy_score(value):
    if isinstance(value, bool):
        return None
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return score if score in set(SCORE_BY_HINT_LEVEL.values()) else None


def _safe_nonnegative_count(value):
    if isinstance(value, bool):
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, count)


def _normalize_mission_mapping(raw_mapping, value_normalizer, omit_zero=False):
    normalized = {}
    if not isinstance(raw_mapping, dict):
        return normalized

    for raw_id, raw_value in raw_mapping.items():
        try:
            mission_id = normalize_mission_id(raw_id)
        except ValueError:
            continue
        value = value_normalizer(raw_value)
        if value is None or (omit_zero and value == 0):
            continue
        normalized[mission_id] = value
    return normalized


def _normalize_mission_list(raw_ids):
    normalized = []
    seen = set()
    if not isinstance(raw_ids, (list, tuple, set)):
        return normalized

    for raw_id in raw_ids:
        try:
            mission_id = normalize_mission_id(raw_id)
        except ValueError:
            continue
        if mission_id not in seen:
            seen.add(mission_id)
            normalized.append(mission_id)
    return normalized


def create_reward_state(legacy_completed=None):
    """Create a fresh reward state.

    ``legacy_completed`` is used only when migrating a save that predates the
    reward system.  Those missions remain completed but are not awarded a score
    that we cannot reconstruct faithfully.
    """
    return {
        'version': REWARD_STATE_VERSION,
        'keys': dict(INITIAL_KEYS),
        'mission_hints': {},
        'mission_scores': {},
        'mission_wrong_answers': {},
        'legacy_unscored_missions': _normalize_mission_list(legacy_completed or []),
    }


def normalize_reward_state(state, legacy_completed=None):
    """Return a sanitized reward-state dictionary.

    Missing/invalid states are treated as legacy saves.  Existing reward states
    are repaired field-by-field without retroactively marking their completed
    missions as legacy.
    """
    if not isinstance(state, dict):
        return create_reward_state(legacy_completed=legacy_completed)

    normalized = create_reward_state()

    raw_keys = state.get('keys')
    if isinstance(raw_keys, dict):
        normalized['keys'] = {
            key: _safe_key_count(raw_keys.get(key), INITIAL_KEYS[key])
            for key in KEY_TYPES
        }

    normalized['mission_hints'] = _normalize_mission_mapping(
        state.get('mission_hints'),
        _safe_hint_level,
        omit_zero=True,
    )
    try:
        raw_version = int(state.get('version', 1))
    except (TypeError, ValueError):
        raw_version = 1
    score_normalizer = _safe_score if raw_version >= 2 else _safe_legacy_score
    normalized['mission_scores'] = _normalize_mission_mapping(
        state.get('mission_scores'),
        score_normalizer,
    )
    normalized['mission_wrong_answers'] = _normalize_mission_mapping(
        state.get('mission_wrong_answers'),
        _safe_nonnegative_count,
        omit_zero=True,
    )
    normalized['legacy_unscored_missions'] = _normalize_mission_list(
        state.get('legacy_unscored_missions', [])
    )

    # A scored mission is no longer "legacy unscored", even if a malformed save
    # listed it in both places.
    scored = set(normalized['mission_scores'])
    normalized['legacy_unscored_missions'] = [
        mission_id
        for mission_id in normalized['legacy_unscored_missions']
        if mission_id not in scored
    ]

    return normalized


class HintSystem:
    """Own the mutable key/hint/score state for one player save."""

    def __init__(self, state=None, legacy_completed=None):
        self.state = normalize_reward_state(state, legacy_completed=legacy_completed)

    def to_dict(self):
        return deepcopy(self.state)

    def get_key_count(self, key_type):
        if key_type not in KEY_TYPES:
            raise ValueError(f'unknown key type: {key_type}')
        return self.state['keys'][key_type]

    def set_campaign_initial_keys(self, campaign_mode):
        """Apply the mode-specific starting key budget without touching progress.

        Student registration calls this only before any mission has started.
        Keeping the operation here guarantees that changing the initial budget
        cannot accidentally rewrite hints, scores or wrong-answer penalties.
        """
        self.state['keys'] = initial_keys_for_campaign(campaign_mode)
        return dict(self.state['keys'])

    def award_keys(self, key_type, amount):
        """Add a positive number of keys and return the updated count.

        One-off exploration rewards use this path so they never affect mission
        hint levels or mission scores.
        """
        if key_type not in KEY_TYPES:
            raise ValueError(f'unknown key type: {key_type}')
        if isinstance(amount, bool):
            raise ValueError('amount must be a positive integer')
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValueError('amount must be a positive integer') from None
        if amount <= 0:
            raise ValueError('amount must be a positive integer')
        self.state['keys'][key_type] += amount
        return self.state['keys'][key_type]

    def get_hint_level(self, mission_id):
        mission_id = normalize_mission_id(mission_id)
        return self.state['mission_hints'].get(mission_id, 0)

    def get_required_key(self, hint_level):
        if hint_level not in KEY_FOR_HINT_LEVEL:
            raise ValueError('hint_level must be 1, 2 or 3')
        return KEY_FOR_HINT_LEVEL[hint_level]

    def find_fallback_key(self, hint_level):
        """Return a stronger available substitute, or None.

        This never returns the preferred key itself and never allows weaker
        keys to substitute for stronger ones.
        """
        required = self.get_required_key(hint_level)
        candidates = KEY_CANDIDATES_BY_HINT_LEVEL[hint_level]
        required_index = candidates.index(required)
        for key_type in candidates[required_index + 1:]:
            if self.get_key_count(key_type) > 0:
                return key_type
        return None

    def get_unlock_offer(self, mission_id, hint_level, mission_completed=False):
        """Describe what would happen without mutating state.

        ``confirmation_required`` is returned whenever a stronger fallback key
        would be needed.  UI code can show that exact key to the player and call
        ``unlock_hint(..., allow_fallback=True)`` only after confirmation.
        """
        mission_id = normalize_mission_id(mission_id)
        if hint_level not in KEY_FOR_HINT_LEVEL:
            raise ValueError('hint_level must be 1, 2 or 3')

        current_level = self.get_hint_level(mission_id)
        required_key = self.get_required_key(hint_level)

        base = {
            'mission_id': mission_id,
            'hint_level': hint_level,
            'current_level': current_level,
            'required_key': required_key,
            'key_to_spend': None,
            'fallback': False,
        }

        if hint_level <= current_level:
            return {**base, 'status': 'already_unlocked'}

        if mission_completed:
            return {**base, 'status': 'mission_completed'}

        if hint_level != current_level + 1:
            return {**base, 'status': 'previous_hint_locked'}

        if self.get_key_count(required_key) > 0:
            return {
                **base,
                'status': 'ready',
                'key_to_spend': required_key,
            }

        fallback_key = self.find_fallback_key(hint_level)
        if fallback_key is not None:
            return {
                **base,
                'status': 'confirmation_required',
                'key_to_spend': fallback_key,
                'fallback': True,
            }

        return {**base, 'status': 'no_key_available'}

    def can_unlock_hint(
        self,
        mission_id,
        hint_level,
        mission_completed=False,
        allow_fallback=False,
    ):
        offer = self.get_unlock_offer(
            mission_id,
            hint_level,
            mission_completed=mission_completed,
        )
        if offer['status'] in ('ready', 'already_unlocked'):
            return True
        return allow_fallback and offer['status'] == 'confirmation_required'

    def unlock_hint(
        self,
        mission_id,
        hint_level,
        mission_completed=False,
        allow_fallback=False,
    ):
        """Unlock one sequential hint and charge at most one key.

        Reopening an already unlocked hint is free.  Fallback consumption is
        impossible unless the caller explicitly passes ``allow_fallback=True``.
        """
        offer = self.get_unlock_offer(
            mission_id,
            hint_level,
            mission_completed=mission_completed,
        )
        status = offer['status']

        if status == 'already_unlocked':
            return {
                **offer,
                'charged_key': None,
                'new_level': offer['current_level'],
            }

        if status == 'confirmation_required' and not allow_fallback:
            return {
                **offer,
                'charged_key': None,
                'new_level': offer['current_level'],
            }

        if status not in ('ready', 'confirmation_required'):
            return {
                **offer,
                'charged_key': None,
                'new_level': offer['current_level'],
            }

        key_to_spend = offer['key_to_spend']
        if self.state['keys'][key_to_spend] <= 0:
            # Defensive re-check in case state was modified between offer and
            # confirmation.
            refreshed = self.get_unlock_offer(
                mission_id,
                hint_level,
                mission_completed=mission_completed,
            )
            return {
                **refreshed,
                'charged_key': None,
                'new_level': refreshed['current_level'],
            }

        self.state['keys'][key_to_spend] -= 1
        self.state['mission_hints'][offer['mission_id']] = hint_level

        return {
            **offer,
            'status': 'unlocked',
            'charged_key': key_to_spend,
            'new_level': hint_level,
        }

    def score_for_hint_level(self, hint_level):
        if hint_level not in SCORE_BY_HINT_LEVEL:
            raise ValueError('hint_level must be between 0 and 3')
        return SCORE_BY_HINT_LEVEL[hint_level]

    def get_wrong_answer_count(self, mission_id):
        mission_id = normalize_mission_id(mission_id)
        return self.state['mission_wrong_answers'].get(mission_id, 0)

    def get_current_mission_score(self, mission_id):
        """Return the score currently available before mission completion.

        Hint penalties and wrong-answer penalties are cumulative. The score is
        clamped at zero so repeated guessing can never create a negative score.
        """
        mission_id = normalize_mission_id(mission_id)
        if mission_id in self.state['mission_scores']:
            return self.state['mission_scores'][mission_id]
        base_score = self.score_for_hint_level(self.get_hint_level(mission_id))
        return max(
            MIN_MISSION_SCORE,
            base_score - self.get_wrong_answer_count(mission_id),
        )

    def record_wrong_answer(self, mission_id, amount=WRONG_ANSWER_PENALTY):
        """Record one or more rejected final-answer submissions.

        A finalized mission is immutable. For an active mission every rejected
        final-answer submission costs one point, including malformed/typo
        answers, because the final-answer field is itself part of the assessed
        interpretation.
        """
        mission_id = normalize_mission_id(mission_id)
        if isinstance(amount, bool):
            raise ValueError('amount must be a positive integer')
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValueError('amount must be a positive integer') from None
        if amount <= 0:
            raise ValueError('amount must be a positive integer')

        if mission_id in self.state['mission_scores']:
            frozen_score = self.state['mission_scores'][mission_id]
            return {
                'mission_id': mission_id,
                'applied': 0,
                'wrong_answers': self.get_wrong_answer_count(mission_id),
                'score_before': frozen_score,
                'current_score': frozen_score,
                'score_loss': 0,
                'finalized': True,
            }

        score_before = self.get_current_mission_score(mission_id)
        new_count = self.get_wrong_answer_count(mission_id) + amount
        self.state['mission_wrong_answers'][mission_id] = new_count
        score_after = self.get_current_mission_score(mission_id)
        return {
            'mission_id': mission_id,
            'applied': amount,
            'wrong_answers': new_count,
            'score_before': score_before,
            'current_score': score_after,
            'score_loss': score_before - score_after,
            'finalized': False,
        }

    def get_total_wrong_answers(self, mission_ids=None):
        if mission_ids is None:
            return sum(self.state['mission_wrong_answers'].values())
        total = 0
        for mission_id in mission_ids:
            total += self.get_wrong_answer_count(mission_id)
        return total

    def finalize_mission_score(self, mission_id):
        """Freeze one mission score and return it, or None for legacy missions."""
        mission_id = normalize_mission_id(mission_id)

        if mission_id in self.state['mission_scores']:
            return self.state['mission_scores'][mission_id]

        if mission_id in self.state['legacy_unscored_missions']:
            return None

        score = self.get_current_mission_score(mission_id)
        self.state['mission_scores'][mission_id] = score
        return score

    def finalize_completed_missions(self, completed_missions):
        """Freeze scores for all completed non-legacy missions."""
        finalized = {}
        for raw_id in completed_missions or []:
            mission_id = normalize_mission_id(raw_id)
            score = self.finalize_mission_score(mission_id)
            if score is not None:
                finalized[mission_id] = score
        return finalized

    def sync_completed_missions(self, completed_missions, tracked_missions=None):
        """Synchronize completion with the staged reward-system rollout.

        Only missions whose hint UI is already integrated may receive a score.
        Any mission completed before its integration is marked legacy-unscored,
        because its historic hint usage cannot be reconstructed faithfully.

        ``tracked_missions`` is injectable for tests and staged rollouts; runtime
        defaults to TRACKED_HINT_MISSIONS.
        """
        tracked_raw = TRACKED_HINT_MISSIONS if tracked_missions is None else tracked_missions
        tracked = {normalize_mission_id(mission_id) for mission_id in tracked_raw}
        legacy = self.state['legacy_unscored_missions']
        legacy_set = set(legacy)
        finalized = {}

        for raw_id in completed_missions or []:
            mission_id = normalize_mission_id(raw_id)
            if mission_id in tracked:
                score = self.finalize_mission_score(mission_id)
                if score is not None:
                    finalized[mission_id] = score
                continue

            if (
                mission_id not in self.state['mission_scores']
                and mission_id not in legacy_set
            ):
                legacy.append(mission_id)
                legacy_set.add(mission_id)

        return finalized

    def get_mission_score(self, mission_id):
        mission_id = normalize_mission_id(mission_id)
        return self.state['mission_scores'].get(mission_id)

    def get_total_score(self):
        return sum(self.state['mission_scores'].values())

    def get_max_score(self, total_missions=40):
        try:
            total_missions = int(total_missions)
        except (TypeError, ValueError):
            raise ValueError('total_missions must be a non-negative integer') from None
        if total_missions < 0:
            raise ValueError('total_missions must be a non-negative integer')
        return total_missions * SCORE_BY_HINT_LEVEL[0]
