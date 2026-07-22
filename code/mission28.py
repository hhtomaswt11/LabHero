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
    MISSION28_METHOD,
    MISSION28_GROWTH_OBJECTIVE,
    MISSION28_BLOCKED_CARBON_SOURCE,
    MISSION28_CANDIDATE_CARBON_SOURCES,
    MISSION28_SWEEP_VALUES,
    MISSION28_REQUIRED_TRACKED_FLUXES,
    MISSION28_MIN_FIRST_GROWTH,
    MISSION28_MAX_FINAL_GROWTH,
    MISSION28_MIN_GROWTH_DROP,
    MISSION28_MIN_CHANGED_FLUXES,
)


class Mission28_info:
    """Mission 28 — Alternative Carbon Source Sweep.

    Third Dr. Luna mission. The player must combine a deliberate base medium
    change with a Bound Sweep: remove glucose, choose a candidate alternative
    carbon source, then read whether that source creates a real limitation trend.
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

        self.mission28 = '28' in self.missions_activated

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
            title='Mission 28',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 28 Briefing',
            width=1280,
        )

        candidate_text = ', '.join(MISSION28_CANDIDATE_CARBON_SOURCES)
        tracked_flux_text = ', '.join(MISSION28_REQUIRED_TRACKED_FLUXES)
        sweep_values_text = ', '.join(str(value).rstrip('0').rstrip('.') for value in MISSION28_SWEEP_VALUES)

        menu_text.add.label(
            f"""
            Mission 28: Alternative Carbon Source Sweep.

            You already tested oxygen levels and glucose limitation. Now Dr. Luna
            wants a harder medium experiment: design a carbon-source replacement
            test instead of following a fixed recipe.

            Scientific goal:
            The cell normally depends on a carbon source from the medium. For this
            experiment, create a controlled situation where the usual carbon input
            is no longer available, then test whether one alternative source can
            support growth across different availability levels.

            Keep the biological setup controlled:
            - {MISSION28_METHOD}
            - {MISSION28_GROWTH_OBJECTIVE}
            - no gene knockouts
            - avoid unrelated environment changes

            In Bound Sweep Setup, choose one candidate carbon-source lower bound:
            {candidate_text}

            Values tested: {sweep_values_text}

            Production Flux evidence required:
            {tracked_flux_text}

            Optional hint: do not choose the source by name only. A good candidate
            should be consumed when available, rescue growth at high availability,
            and lose that rescue as availability approaches zero.
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
            'Mission 28: Alternative Carbon Source Sweep',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Luna now wants you to design the starting medium before the sweep.

            Question:
            Can the cell switch away from its usual carbon source and still grow
            when a different carbon source is available?

            Base setup:
            - Method: {MISSION28_METHOD}
            - Objective: {MISSION28_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: controlled carbon-source replacement only

            Bound Sweep Setup:
            - Variable: choose one candidate carbon-source lower bound
            - Candidates: {candidate_text}
            - Values: {sweep_values_text}

            Production Flux evidence required:
            {tracked_flux_text}

            Your report should prove three things:
            - the usual carbon input was removed cleanly
            - the candidate source is actually consumed and can rescue growth
            - growth and secretion change as that candidate becomes limited
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 28 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission28:
            menu.add.button('Deliver Carbon Source Sweep', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            if '27' in self.missions_completed:
                menu.add.button('Activate Mission', action=self.activate_mission28, background_color=(50, 100, 100))
            else:
                menu.add.label('Complete Mission 27 before activating this mission.', font_color=(150, 40, 40))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission28(self):
        if '27' not in self.missions_completed:
            self.failed.play()
            animation_text_save('Complete Mission 27 first.', time=2500)
            return

        clear_bound_sweep()
        clear_mission28_bound_sweep_check()
        self.mission28 = True
        if '28' not in self.missions_activated:
            self.missions_activated.insert(0, '28')
        animation_text_save('Mission 28 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission28_bound_sweep_check()

        if (not report_data
                or report_data.get('mission_id') != '28'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 28 carbon-source sweep first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '28' not in self.missions_completed:
                self.missions_completed.insert(0, '28')
            animation_text_save('Congratulations! Mission 28 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('base_medium_ready'):
            animation_text_save('The starting medium is not a clean carbon-source replacement yet.', time=3200)
        elif not report_data.get('candidate_sweep_selected'):
            animation_text_save('Sweep one candidate carbon-source lower bound, not an unrelated exchange.', time=3000)
        elif not report_data.get('tracking_ready'):
            animation_text_save('Select the full Production Flux panel before running the sweep.', time=3000)
        elif not report_data.get('all_points_returned'):
            animation_text_save('The carbon-source sweep is missing result points.', time=3000)
        elif not report_data.get('source_consumed'):
            animation_text_save('This candidate is not being consumed strongly enough. Check the sweep trend.', time=3000)
        elif not report_data.get('first_growth_viable'):
            animation_text_save('At high availability this source does not rescue growth enough.', time=3000)
        elif not report_data.get('growth_decreased'):
            animation_text_save('Growth did not drop enough as the source became limited.', time=3000)
        elif not report_data.get('final_growth_low'):
            animation_text_save('The final point should show severe/no growth.', time=3000)
        elif not report_data.get('profile_changed'):
            animation_text_save('Not enough tracked products/byproducts changed across the sweep.', time=3000)
        else:
            animation_text_save('Almost there. Inspect the full carbon-source trend.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
