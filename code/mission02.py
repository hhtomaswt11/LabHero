import pygame
import pygame_menu

from answer_penalty import penalize_wrong_answer

from async_menu import run_menu
from button import Button
from functions import animation_text_save
from options_values import mytheme
from save_load import (
    clear_mission02_source_comparison_check,
    load_mission02_source_comparison_check,
    save_file,
)
from settings import *
from simulation import (
    build_mission02_evidence_report_text,
    is_mission02_unlocked,
    mission02_answer_matches,
    normalise_mission02_answer,
)
from timers import Timer
from utils import get_dialogue_portrait, get_dialogue_text_surface, get_resource_path, prepare_dialogue_text


class Mission02:
    """Compatibility dialogue for Mission 02.

    Mission 02 is normally launched through Dr. Martinez after Mission 01, but
    this class remains available for older map/code references. It now uses the
    same scientist and scientific wording as the active mission flow.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu

        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.font_nome = pygame.font.Font(font_path, 24)
        self.screen = pygame.display.get_surface()
        self.timer = Timer(200)
        self.menu = Mission02_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        step_locked = [
            "Dr. Martinez is still waiting for the oxygen comparison.",
            "Complete Mission 01 before beginning the carbon-source investigation.",
        ]
        step_intro = [
            "I'm Dr. Martinez. Our E. coli culture has lost access to glucose.",
            "Several alternatives are available, but they do not support growth equally.",
            "Can you design a fair comparison and identify the strongest substitute?",
        ]
        step_active = [
            "Have you completed a controlled comparison of the candidate carbon sources?",
            "Show me the evidence and the conclusion you reached.",
        ]
        step_complete = [
            f"Excellent work, {self.player.player_name}!",
            "You showed how environmental conditions change predicted microbial growth.",
            "Dr. Silva can now introduce you to controlled genetic perturbations in Mission 03.",
        ]

        self.input()
        if not self.player.is_mission_unlocked('02'):
            self.menu_message(step_locked, buttons=False)
        elif '02' in self.missions_completed:
            self.menu_message(step_complete, buttons=False)
        elif '02' in self.missions_activated:
            self.menu_message(step_active)
        else:
            self.menu_message(step_intro)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image_path = get_resource_path('graphics/dialogues/martinez.jpg')
        image = get_dialogue_portrait(image_path)
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_nome, 'Dr. Martinez')
        self.screen.blit(name, (40, 677))

        for line, msg in enumerate(message):
            msg = prepare_dialogue_text(msg, self.player.player_name)
            surf = get_dialogue_text_surface(self.font, msg)
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                self.pending = self.menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission02_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()

        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.index = 0
        self.timer = Timer(200)
        self.mission02 = (
            '02' in self.missions_activated
            or '02' in self.missions_completed
        )

        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)

        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)

    @staticmethod
    def _key_label(key_type):
        return str(key_type).capitalize()

    def _mission02_completed(self):
        return '02' in self.missions_completed

    def _save_reward_progress(self):
        # HintSystem mutates the Player-owned reward state in place. Persist
        # immediately so a purchased hint can never be charged twice after a
        # reload/crash between the hint purchase and mission completion.
        self.player.reward_state = self.player.hint_system.state
        save_file(self.player.get_save_data())

    def _open_hint_menu(self, source_menu, target_menu):
        # pygame-menu 4.4.3 implements submenu buttons through Menu._open().
        # We use the same transition here because access must be decided at
        # click time before the protected submenu is opened.
        source_menu._open(target_menu)

    def _notify_hint_access_failure(self, status, hint_level):
        if status == 'previous_hint_locked':
            animation_text_save(
                f'Unlock Mission 02 Hint {hint_level - 1} first.',
                time=2600,
            )
            return

        if status == 'mission_completed':
            animation_text_save(
                'Mission 02 is complete. New hints can no longer be unlocked.',
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
                f'No {candidates} Key is available for Mission 02 Hint {hint_level}.',
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
            '02',
            hint_level,
            mission_completed=self._mission02_completed(),
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
            f'Mission 02 Hint {hint_level} unlocked with 1 {charged_key} Key.',
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
            '02',
            hint_level,
            mission_completed=self._mission02_completed(),
            allow_fallback=True,
        )

        if result['status'] == 'unlocked':
            self._save_reward_progress()
            charged_key = self._key_label(result['charged_key'])
            animation_text_save(
                f'Mission 02 Hint {hint_level} unlocked with 1 {charged_key} Key.',
                time=2600,
            )
            # Remove the confirmation screen from history so Back from the hint
            # returns to the screen where the player requested it.
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
            theme=mytheme,
            title=f'Mission 02 Hint {hint_level} - Key Substitution',
            width=1280,
        overflow=(False, True),
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

    def _request_hint_access(self, hint_level, source_menu, target_menu):
        offer = self.player.hint_system.get_unlock_offer(
            '02',
            hint_level,
            mission_completed=self._mission02_completed(),
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

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 02',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('02'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 02 is locked. Complete Mission 01 with Dr. Martinez before beginning the carbon-source investigation.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        menu_text = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 02 Briefing',
            width=1280,
        overflow=(False, True),
        )

        hint_3 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 02 Hint 3',
            width=1280,
        overflow=(False, True),
        )
        hint_3.add.label(
            """
            Technical hint: use FBA with the biomass objective. Make glucose unavailable, enable the uptake of exactly one candidate at a time and keep the genes, oxygen availability and every unrelated environmental bound unchanged.

            Use the same molar uptake allowance for every candidate. In this simulator, opening the uptake of a candidate that is closed by default gives it a lower bound of -10.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint_3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint_2 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 02 Hint 2',
            width=1280,
        overflow=(False, True),
        )
        hint_2.add.label(
            """
            Experimental hint: a replacement is not the same as a supplement. The usual carbon source must no longer be available while each alternative is tested separately through its exchange reaction.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint_2.add.button(
            'Reveal technical hint (Gold Key if locked)',
            self._request_hint_access,
            3,
            hint_2,
            hint_3,
            background_color=(255, 215, 0, 255),
            font_color='black',
        )
        hint_2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint_1 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 02 Hint 1',
            width=1280,
        overflow=(False, True),
        )
        hint_1.add.label(
            """
            Conceptual hint: a fair experiment changes the factor being investigated while keeping the remaining assumptions comparable. Decide what must stay constant before comparing the growth values.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint_1.add.button(
            'Reveal next hint (Silver Key if locked)',
            self._request_hint_access,
            2,
            hint_1,
            hint_2,
            background_color=(255, 215, 0, 255),
            font_color='black',
        )
        hint_1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu_text.add.label(
            """
            The culture's usual glucose supply is unavailable. Use the metabolic model to determine which candidate carbon source best restores predicted growth.

            Your conclusion must come from a fair comparison rather than from testing unrelated combinations or guessing. Decide which part of the setup should change between trials, which assumptions should remain comparable and what result provides evidence for growth.

            The candidates should be compared on equal terms. Think carefully about what "equal terms" means when nutrient availability is represented by reaction bounds.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
        )
        menu_text.add.label(
            'Concepts to observe:',
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(100, 0),
            background_color='gold',
            font_color='black',
            font_size=30,
            padding=(25, 25, 25, 25),
        )
        menu_text.add.label(
            """
            - Replacing a nutrient is different from supplying it alongside the original source.

            - Exchange reactions represent the connection between the model and its environment.

            - Controlled comparisons keep unrelated biological assumptions consistent.

            - Predicted biomass formation can be used as evidence of how well each condition supports growth.

            - A defensible conclusion should be supported by the full candidate comparison.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
        )
        menu_text.add.button(
            'Optional Hints (Bronze Key if locked)',
            self._request_hint_access,
            1,
            menu_text,
            hint_1,
            background_color=(255, 215, 0, 255),
            font_color='black',
        )
        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 02: Restore growth without glucose.',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            """
            The usual glucose supply is no longer available. Determine which candidate carbon source best supports predicted E. coli growth when used as its replacement.

            Candidate carbon sources:

            - malate                             - lactate
            - glutamate                        - glutamine
            - fumarate                         - fructose
            - ethanol                            - 2-oxoglutarate
            - acetaldehyde                    - acetate

            Build comparable trials, inspect the growth evidence and submit the candidate supported by the results.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )
        menu.add.button(
            'Mission 02 Briefing',
            menu_text,
            font_color='black',
            background_color=(255, 215, 0, 255),
        )
        menu.add.button(
            'Optional Hints (Bronze Key if locked)',
            self._request_hint_access,
            1,
            menu,
            hint_1,
            font_color='black',
            background_color=(230, 230, 180),
        )
        menu.add.vertical_margin(30)

        if self.mission02:
            report_data = load_mission02_source_comparison_check()
            menu.add.label(
                build_mission02_evidence_report_text(report_data),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=23,
            )
            menu.add.vertical_margin(25)

            menu.add.text_input(
                'Best substitute: ',
                default='',
                input_underline='_',
                maxchar=24,
                onreturn=self.deliver_results,
            )
            menu.add.vertical_margin(30)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button(
                'Activate Mission',
                action=self.activate_mission02,
                background_color=(50, 100, 100),
            )

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission02(self):
        if not self.player.is_mission_unlocked('02'):
            self.failed.play()
            animation_text_save('Complete Mission 01 before starting Mission 02.', time=3000)
            return

        # Activation is idempotent. A duplicate action must never clear the
        # candidate trials already recorded for the current mission.
        if '02' in self.missions_completed:
            self.mission02 = True
            animation_text_save('Mission 02 is already completed.', time=2500)
            return
        if '02' in self.missions_activated:
            self.mission02 = True
            animation_text_save('Mission 02 is already active.', time=2500)
            return

        clear_mission02_source_comparison_check()
        self.mission02 = True
        self.missions_activated.insert(0, '02')
        animation_text_save('Mission 02 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('02'):
            self.failed.play()
            animation_text_save('Complete Mission 01 before delivering Mission 02.', time=3000)
            return
        if '02' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 02 before delivering results.', time=3000)
            return

        report_data = load_mission02_source_comparison_check()

        if not report_data or report_data.get('mission_id') != '02' or report_data.get('check_version') != 2:
            self.failed.play()
            animation_text_save('Run controlled carbon-source trials before delivering.', time=3200)
            return

        if not report_data.get('evidence_ready'):
            self.failed.play()
            missing = report_data.get('missing_candidates') or []
            if missing:
                completed = report_data.get('valid_trial_count', 0)
                required = report_data.get('required_trial_count', 0)
                animation_text_save(
                    f'Comparison incomplete: {completed}/{required} valid candidates recorded.',
                    time=3400,
                )
            elif report_data.get('current_issues'):
                animation_text_save('The latest trial was not controlled. Review the evidence report.', time=3400)
            else:
                animation_text_save('Review the controlled comparison before delivering.', time=3200)
            return

        if normalise_mission02_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter one candidate carbon-source name from the mission list.', time=3000)
            penalize_wrong_answer(self.player, '02')
            return

        if not mission02_answer_matches(answer, report_data):
            self.failed.play()
            animation_text_save('That conclusion is not supported by the recorded growth evidence.', time=3200)
            penalize_wrong_answer(self.player, '02')
            return

        self.success.play()
        if '02' not in self.missions_completed:
            self.missions_completed.insert(0, '02')
        animation_text_save('Congratulations! Mission 02 completed!', time=2500)
        save_file(self.player.get_save_data())

    def check_results(self, answer):
        return mission02_answer_matches(
            answer,
            load_mission02_source_comparison_check(),
        )

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback

    async def update(self):
        self.input()
        await self.setup()
