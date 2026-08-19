"""Reusable pygame-menu access gate for LabHero mission hints.

The economic rules stay in :mod:`hint_system`.  This module only owns the UI
flow around those rules: opening an already purchased hint, charging the
preferred key, asking for explicit confirmation before a stronger-key fallback,
and saving immediately after a successful purchase.
"""

import pygame_menu

from functions import animation_text_save
from hint_system import normalize_mission_id
from save_load import save_file


class MissionHintAccess:
    """Connect one mission's three hint menus to the central HintSystem."""

    def __init__(self, player, mission_id, missions_completed, theme):
        self.player = player
        self.mission_id = normalize_mission_id(mission_id)
        self.missions_completed = missions_completed
        self.theme = theme

    @staticmethod
    def _key_label(key_type):
        return str(key_type).capitalize()

    @property
    def mission_label(self):
        return f'Mission {self.mission_id}'

    def _mission_completed(self):
        return self.mission_id in self.missions_completed

    def _save_reward_progress(self):
        # HintSystem mutates Player-owned state in place.  Persist immediately
        # so reload/crash cannot charge the same purchased hint twice.
        self.player.reward_state = self.player.hint_system.state
        save_file(self.player.get_save_data())

    @staticmethod
    def _open_hint_menu(source_menu, target_menu):
        # pygame-menu 4.4.3 implements submenu buttons through Menu._open().
        # Access is checked at click time before opening the protected menu.
        source_menu._open(target_menu)

    def _notify_hint_access_failure(self, status, hint_level):
        if status == 'previous_hint_locked':
            animation_text_save(
                f'Unlock {self.mission_label} Hint {hint_level - 1} first.',
                time=2600,
            )
            return

        if status == 'mission_completed':
            animation_text_save(
                f'{self.mission_label} is complete. New hints can no longer be unlocked.',
                time=3000,
            )
            return

        if status == 'no_key_available':
            candidates = {
                1: 'Bronze, Silver or Gold',
                2: 'Silver or Gold',
                3: 'Gold',
            }[hint_level]
            animation_text_save(
                f'No {candidates} Key is available for {self.mission_label} Hint {hint_level}.',
                time=3200,
            )
            return

        animation_text_save('That hint cannot be unlocked right now.', time=2600)

    def _unlock_hint_and_open(
        self,
        hint_level,
        source_menu,
        target_menu,
        allow_fallback=False,
    ):
        result = self.player.hint_system.unlock_hint(
            self.mission_id,
            hint_level,
            mission_completed=self._mission_completed(),
            allow_fallback=allow_fallback,
        )

        if result['status'] == 'already_unlocked':
            self._open_hint_menu(source_menu, target_menu)
            return result

        if result['status'] != 'unlocked':
            self._notify_hint_access_failure(result['status'], hint_level)
            return result

        self._save_reward_progress()
        charged_key = self._key_label(result['charged_key'])
        animation_text_save(
            f'{self.mission_label} Hint {hint_level} unlocked with 1 {charged_key} Key.',
            time=2600,
        )
        self._open_hint_menu(source_menu, target_menu)
        return result

    def _confirm_fallback_hint(
        self,
        hint_level,
        source_menu,
        confirmation_menu,
        target_menu,
    ):
        result = self.player.hint_system.unlock_hint(
            self.mission_id,
            hint_level,
            mission_completed=self._mission_completed(),
            allow_fallback=True,
        )

        if result['status'] == 'unlocked':
            self._save_reward_progress()
            charged_key = self._key_label(result['charged_key'])
            animation_text_save(
                f'{self.mission_label} Hint {hint_level} unlocked with 1 {charged_key} Key.',
                time=2600,
            )
            confirmation_menu.reset(1)
            self._open_hint_menu(source_menu, target_menu)
            return result

        if result['status'] == 'already_unlocked':
            confirmation_menu.reset(1)
            self._open_hint_menu(source_menu, target_menu)
            return result

        self._notify_hint_access_failure(result['status'], hint_level)
        return result

    def _build_fallback_confirmation(
        self,
        hint_level,
        source_menu,
        target_menu,
        offer,
    ):
        required = self._key_label(offer['required_key'])
        fallback = self._key_label(offer['key_to_spend'])
        confirmation = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=self.theme,
            title=f'{self.mission_label} Hint {hint_level} - Key Substitution',
            width=1280,
        )
        confirmation.add.vertical_margin(45)
        confirmation.add.label(
            f'No {required} Keys are available.\n\nUse 1 {fallback} Key instead?',
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            padding=(25, 25, 25, 25),
            background_color='white',
            font_size=30,
        )
        confirmation.add.button(
            f'Use 1 {fallback} Key',
            self._confirm_fallback_hint,
            hint_level,
            source_menu,
            confirmation,
            target_menu,
            background_color=(255, 215, 0, 255),
            font_color='black',
        )
        confirmation.add.button(
            'Cancel',
            pygame_menu.events.BACK,
            background_color=(70, 70, 70),
        )
        return confirmation

    def request(self, hint_level, source_menu, target_menu):
        """Open/reveal one hint, enforcing keys and sequential progression."""
        offer = self.player.hint_system.get_unlock_offer(
            self.mission_id,
            hint_level,
            mission_completed=self._mission_completed(),
        )
        status = offer['status']

        if status == 'already_unlocked':
            self._open_hint_menu(source_menu, target_menu)
            return offer

        if status == 'ready':
            return self._unlock_hint_and_open(
                hint_level,
                source_menu,
                target_menu,
                allow_fallback=False,
            )

        if status == 'confirmation_required':
            confirmation = self._build_fallback_confirmation(
                hint_level,
                source_menu,
                target_menu,
                offer,
            )
            self._open_hint_menu(source_menu, confirmation)
            return offer

        self._notify_hint_access_failure(status, hint_level)
        return offer
