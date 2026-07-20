import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from async_menu import run_menu
from utils import *
from simulation import (
    MISSION24_BASELINE_METHOD,
    MISSION24_TARGET_METHOD,
    MISSION24_GROWTH_OBJECTIVE,
    MISSION24_REQUIRED_TRACKED_FLUXES,
)


class Mission24_info:
    """Mission 24 — Method Comparison.

    Fourth Dr. Vega mission. The player compares the same model setup under two
    simulation methods: FBA versus pFBA.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)

        self.mission24 = '24' in self.missions_activated

        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)

        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 24',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 24 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Mission 24: Method Comparison.

            You have already compared environments, knockouts and objectives.
            Now compare the simulation method itself.

            FBA finds one valid flux distribution that optimizes the objective.
            pFBA keeps the same objective goal, but prefers a simpler/parsimony
            flux distribution.

            Keep objective, genes and environment unchanged in both runs.
            Change only the method from {MISSION24_BASELINE_METHOD} to
            {MISSION24_TARGET_METHOD}. Track the same production-flux panel in
            both runs so Compare Runs can show the flux profile side by side.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
        )
        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)

        tracked_flux_text = ', '.join(MISSION24_REQUIRED_TRACKED_FLUXES)

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 24: Method Comparison',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Vega now wants a method comparison.

            Question:
            What changes when the same growth setup is simulated with FBA and pFBA?

            Run A — FBA baseline:
            - Method: {MISSION24_BASELINE_METHOD}
            - Objective: {MISSION24_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: unchanged
            - Production Flux: track {tracked_flux_text}

            Run B — pFBA method test:
            - Method: {MISSION24_TARGET_METHOD}
            - Objective: {MISSION24_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: unchanged
            - Production Flux: track {tracked_flux_text}

            After the second simulation, open New Results -> Compare Runs.
            The only setup change should be the simulation method.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 24 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission24:
            menu.add.button('Deliver Method Comparison', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            if '23' in self.missions_completed:
                menu.add.button('Activate Mission', action=self.activate_mission24, background_color=(50, 100, 100))
            else:
                menu.add.label('Complete Mission 23 before activating this mission.', font_color=(150, 40, 40))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission24(self):
        if '23' not in self.missions_completed:
            self.failed.play()
            animation_text_save('Complete Mission 23 first.', time=2500)
            return

        clear_compare_runs()
        clear_mission24_comparison_check()
        self.mission24 = True
        if '24' not in self.missions_activated:
            self.missions_activated.insert(0, '24')
        animation_text_save('Mission 24 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission24_comparison_check()

        if (not report_data
                or report_data.get('mission_id') != '24'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 24 comparison first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '24' not in self.missions_completed:
                self.missions_completed.insert(0, '24')
            animation_text_save('Congratulations! Mission 24 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('fba_run_found'):
            animation_text_save('Missing Run A. Use FBA with biomass objective and unchanged setup.', time=3000)
        elif not report_data.get('pfba_run_found'):
            animation_text_save('Missing Run B. Use pFBA with the same objective and setup.', time=3000)
        elif not report_data.get('same_clean_setup'):
            animation_text_save('Keep genes and environment unchanged in both runs.', time=3000)
        elif not report_data.get('same_objective'):
            animation_text_save('Keep the biomass objective in both runs.', time=3000)
        elif not report_data.get('tracking_ready'):
            animation_text_save('Track the full production-flux panel in both runs.', time=3000)
        else:
            animation_text_save('Almost there. Open Compare Runs and check the method comparison.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
