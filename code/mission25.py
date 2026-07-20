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
    MISSION25_METHOD,
    MISSION25_GROWTH_OBJECTIVE,
    MISSION25_OXYGEN_REACTION,
    MISSION25_REQUIRED_TRACKED_FLUXES,
    MISSION25_MIN_GROWTH_DROP,
    MISSION25_MIN_CHANGED_FLUXES,
)


class Mission25_info:
    """Mission 25 — Final Controlled Report.

    Final Dr. Vega mission. The player repeats a familiar environment
    comparison, but now produces a fuller report with growth and production
    flux evidence.
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

        self.mission25 = '25' in self.missions_activated

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
            title='Mission 25',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 25 Briefing',
            width=1280,
        )

        tracked_flux_text = ', '.join(MISSION25_REQUIRED_TRACKED_FLUXES)

        menu_text.add.label(
            f"""
            Mission 25: Final Controlled Report.

            This is Dr. Vega's final comparison task.
            A controlled comparison should change only one variable between
            two simulations. This makes the cause of the result difference clear.

            Use the same setup in both runs: {MISSION25_METHOD}, biomass objective,
            no gene knockouts, and the same Production Flux panel.

            Run A is the aerobic baseline.
            Run B changes only oxygen availability by closing the lower bound of
            {MISSION25_OXYGEN_REACTION}.

            Track this product/byproduct panel in both runs:
            {tracked_flux_text}

            Then open Compare Runs to check both growth and production-profile changes.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
        )
        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 25: Final Controlled Report',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Vega wants one complete controlled report.

            Question:
            How does removing oxygen affect both growth and the product/byproduct profile?

            Run A — aerobic baseline:
            - Method: {MISSION25_METHOD}
            - Objective: {MISSION25_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: unchanged
            - Production Flux: track {tracked_flux_text}

            Run B — oxygen-limited setup:
            - Method: {MISSION25_METHOD}
            - Objective: {MISSION25_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: close only the lower bound of {MISSION25_OXYGEN_REACTION}
            - Production Flux: track {tracked_flux_text}

            After the second simulation, open New Results -> Compare Runs.
            Growth should drop by at least {MISSION25_MIN_GROWTH_DROP:.1f}, and at least
            {MISSION25_MIN_CHANGED_FLUXES} tracked production fluxes should change.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 25 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission25:
            menu.add.button('Deliver Final Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            if '24' in self.missions_completed:
                menu.add.button('Activate Mission', action=self.activate_mission25, background_color=(50, 100, 100))
            else:
                menu.add.label('Complete Mission 24 before activating this mission.', font_color=(150, 40, 40))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission25(self):
        if '24' not in self.missions_completed:
            self.failed.play()
            animation_text_save('Complete Mission 24 first.', time=2500)
            return

        clear_compare_runs()
        clear_mission25_comparison_check()
        self.mission25 = True
        if '25' not in self.missions_activated:
            self.missions_activated.insert(0, '25')
        animation_text_save('Mission 25 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission25_comparison_check()

        if (not report_data
                or report_data.get('mission_id') != '25'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 25 comparison first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '25' not in self.missions_completed:
                self.missions_completed.insert(0, '25')
            animation_text_save('Congratulations! Mission 25 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('baseline_run_found'):
            animation_text_save('Missing Run A. Use the aerobic baseline with the full flux panel.', time=3000)
        elif not report_data.get('oxygen_limited_run_found'):
            animation_text_save('Missing Run B. Close only the oxygen lower bound and run again.', time=3000)
        elif not report_data.get('tracking_ready'):
            animation_text_save('Track the full production-flux panel in both runs.', time=3000)
        elif not report_data.get('growth_decreased'):
            animation_text_save('Growth has not dropped clearly after oxygen limitation yet.', time=3000)
        elif not report_data.get('production_profile_changed'):
            animation_text_save('The production profile has not changed enough yet.', time=3000)
        else:
            animation_text_save('Almost there. Open Compare Runs and check the final report.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
