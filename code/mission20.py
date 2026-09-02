import pygame
import pygame_menu

from answer_penalty import penalize_wrong_answer

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from async_menu import run_menu
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION20_CHECK_VERSION,
    MISSION20_TARGET_METHOD,
    MISSION20_GROWTH_OBJECTIVE,
    MISSION20_OXYGEN_REACTION,
    MISSION20_ACETATE_EXPORT,
    MISSION20_REQUIRED_TRACKED_FLUXES,
    build_mission20_context_report_text,
    initialise_mission20_context_matrix,
    is_mission20_unlocked,
    mission20_answer_matches,
    normalise_mission20_answer,
)


class Mission20_info:
    """Mission 20 — Context-Specific Export Robustness."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission20 = '20' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '20', self.missions_completed, mytheme)

        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 20',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('20'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 20 is locked. Complete Mission 19 before beginning the final context-robustness matrix.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 20 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f'Technical hint: use {MISSION20_TARGET_METHOD}, objective {MISSION20_GROWTH_OBJECTIVE}, all genes active and model-default glucose. Track ' + ', '.join(MISSION20_REQUIRED_TRACKED_FLUXES) + f'. Record all four combinations of {MISSION20_OXYGEN_REACTION} lower bound open/closed and {MISSION20_ACETATE_EXPORT} upper bound open/closed.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 20 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: compare acetate-open versus acetate-closed within each oxygen context. Look at growth, acetate, the remaining export profile and the pFBA diagnostics before comparing the two contexts.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 20 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: the same upper-bound closure can be silent in one feasible optimum and influential in another. Robustness must therefore be evaluated across controlled environmental contexts.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 20 Briefing', width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Rio's final challenge is a controlled two-factor robustness matrix.

            Shared protocol:
            Use {MISSION20_TARGET_METHOD}, the biomass objective, every gene active, model-default glucose and the complete product/byproduct panel. Keep every unrelated environmental bound at its model default.

            Record four visible runs:
            1. Oxygen available; acetate export upper bound open.
            2. Oxygen available; acetate export upper bound closed.
            3. Oxygen uptake lower bound closed; acetate export upper bound open.
            4. Oxygen uptake lower bound closed; acetate export upper bound closed.

            Only oxygen availability and the acetate upper bound may vary. Compare each before/after pair, then identify the oxygen context in which the closure changed the predicted phenotype.

            The final field asks for one concise oxygen context, not an essay.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 20: Context-Specific Export Robustness',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Build a four-run oxygen-by-acetate matrix and determine where the same export closure changes the predicted phenotype.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Controlled factors:\nOxygen uptake: {MISSION20_OXYGEN_REACTION} lower bound open or closed\nAcetate export: {MISSION20_ACETATE_EXPORT} upper bound open or closed\nProduction Flux panel: {", ".join(MISSION20_REQUIRED_TRACKED_FLUXES)}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=24,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 20 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission20:
            report = load_mission20_robustness_report_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '20'
                or report.get('check_version') != MISSION20_CHECK_VERSION
            ):
                report = initialise_mission20_context_matrix()
            menu.add.label(
                build_mission20_context_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.label(
                'Question: In which oxygen context did closing acetate export change the predicted phenotype?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Oxygen context: ',
                default='',
                input_underline='_',
                maxchar=60,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission20, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission20(self):
        if not self.player.is_mission_unlocked('20'):
            self.failed.play()
            animation_text_save('Complete Mission 19 before starting Mission 20.', time=3000)
            return
        if '20' in self.missions_completed:
            return
        if '20' in self.missions_activated:
            self.mission20 = True
            return

        clear_mission20_robustness_report_check()
        initialise_mission20_context_matrix()
        self.mission20 = True
        self.missions_activated.insert(0, '20')
        animation_text_save('Mission 20 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('20'):
            self.failed.play()
            animation_text_save('Complete Mission 19 first!', time=2500)
            return
        if '20' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 20 before delivering a conclusion.', time=2800)
            return

        report = load_mission20_robustness_report_check()
        if (
            not report
            or report.get('mission_id') != '20'
            or report.get('check_version') != MISSION20_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the four current-format Mission 20 runs first.', time=3000)
            return
        if not report.get('all_runs_recorded'):
            self.failed.play()
            animation_text_save('Complete all four oxygen-by-acetate matrix runs.', time=3000)
            return
        if not report.get('same_controlled_setup'):
            self.failed.play()
            animation_text_save('The four runs do not preserve the controlled setup.', time=3000)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible matrix does not support one context-specific response.', time=3000)
            return
        if len(normalise_mission20_answer(answer)) != 1:
            self.failed.play()
            animation_text_save('Enter exactly one oxygen context.', time=2800)
            penalize_wrong_answer(self.player, '20')
            return
        if not mission20_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That context is not supported by the recorded before/after comparisons.', time=3000)
            penalize_wrong_answer(self.player, '20')
            return

        self.success.play()
        if '20' not in self.missions_completed:
            self.missions_completed.insert(0, '20')
        animation_text_save('Congratulations! Mission 20 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
