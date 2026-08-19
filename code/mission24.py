import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from async_menu import run_menu
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION24_CHECK_VERSION,
    MISSION24_METHOD,
    MISSION24_GROWTH_OBJECTIVE,
    MISSION24_SWEEP_REACTION,
    MISSION24_SWEEP_VALUES,
    MISSION24_REQUIRED_TRACKED_FLUXES,
    MISSION24_REQUIRED_MEDIUM_FLUXES,
    build_mission24_export_capacity_report_text,
    initialise_mission24_export_capacity_thresholds,
    is_mission24_unlocked,
    mission24_answer_matches,
    normalise_mission24_answer,
)


class Mission24_info:
    """Mission 24 — Export Capacity Thresholds, Dr. Luna's final mission."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission24 = '24' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '24', self.missions_completed, mytheme)

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
            title='Mission 24',
            width=1280,
        )

        if not is_mission24_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 24 is locked. Complete Mission 23 before beginning Dr. Luna's final sensitivity experiment.",
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
            theme=mytheme, title='Mission 24 Hint 3', width=1280,
        )
        hint3.add.label(
            f"Technical hint: use {MISSION24_METHOD}, objective {MISSION24_GROWTH_OBJECTIVE}, every gene active and a completely default base environment. In Bound Sweep Setup select {MISSION24_SWEEP_REACTION} upper bound and values 25, 20, 10, 0. In Production Flux select " + ', '.join(MISSION24_REQUIRED_TRACKED_FLUXES) + '.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 24 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: first locate the cap that the baseline does not reach. Then find the first tighter cap that is fully used, and inspect which previously absent tracked secretion appears before another route activates at a still tighter cap.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 24 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: an upper bound is non-binding while the optimum stays below it. Once the solution reaches the cap, further restriction can force flux through compensatory export routes.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 24 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Luna now moves from graded uptake limitation to graded export capacity.

            Configure one four-point Bound Sweep:
            - Method: {MISSION24_METHOD}
            - Objective: {MISSION24_GROWTH_OBJECTIVE}
            - Genes: all active
            - Base environment: every lower and upper bound at model default
            - Sweep variable: {MISSION24_SWEEP_REACTION} upper bound
            - Sweep values: {', '.join(f'{value:g}' for value in MISSION24_SWEEP_VALUES)}
            - Production Flux: {', '.join(MISSION24_REQUIRED_TRACKED_FLUXES)}

            The sweep report also records {', '.join(MISSION24_REQUIRED_MEDIUM_FLUXES)} and the pFBA diagnostics for every row.

            Identify the first compensatory tracked secretion that appears when the CO2-export cap becomes binding, before a second route appears at a tighter cap. Submit one concise route.
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
            'Mission 24: Export Capacity Thresholds',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Build one CO2-export capacity curve and identify the first compensatory secretion in the sequence.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 24 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission24_comparison_check()
        report_label_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_label_options['background_color'] = 'white'
        menu.add.label(
            build_mission24_export_capacity_report_text(report),
            **report_label_options,
        )
        menu.add.vertical_margin(20)

        if '24' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission24 or '24' in self.missions_activated:
            self.mission24 = True
            menu.add.label(
                'Question: Which tracked secretion became active at the first binding CO2-export cap, before acetate appeared at a tighter cap?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'First compensatory secretion: ',
                default='',
                input_underline='_',
                maxchar=80,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission24, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission24(self):
        if not is_mission24_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 23 before starting Mission 24.', time=3000)
            return
        if '24' in self.missions_completed:
            return
        if '24' in self.missions_activated:
            self.mission24 = True
            return

        clear_bound_sweep()
        clear_mission24_comparison_check()
        initialise_mission24_export_capacity_thresholds()
        self.mission24 = True
        self.missions_activated.insert(0, '24')
        animation_text_save('Mission 24 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission24_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 23 first!', time=2500)
            return
        if '24' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 24 before delivering a conclusion.', time=2800)
            return

        report = load_mission24_comparison_check()
        if (
            not report
            or report.get('mission_id') != '24'
            or report.get('check_version') != MISSION24_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 24 Bound Sweep first.', time=3000)
            return
        if not report.get('all_points_recorded'):
            self.failed.play()
            animation_text_save('Record all four required CO2 upper-bound points.', time=3000)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible sweep does not yet support the required threshold interpretation.', time=3000)
            return
        if normalise_mission24_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter one unambiguous tracked secretion only.', time=2800)
            return
        if not mission24_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That secretion is not supported as the first compensatory route in the recorded curve.', time=3000)
            return

        self.success.play()
        if '24' not in self.missions_completed:
            self.missions_completed.insert(0, '24')
        animation_text_save('Congratulations! Mission 24 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
