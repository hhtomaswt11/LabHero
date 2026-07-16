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
    MISSION17_METHOD,
    MISSION17_GROWTH_OBJECTIVE,
    MISSION17_TARGET_NUTRIENT,
    MISSION17_TARGET_NUTRIENT_NAME,
    MISSION17_CANDIDATE_NUTRIENTS,
    MISSION17_MAX_GROWTH,
)


class Mission17_info:
    """Mission 17 — Essential Medium Component.

    Dr. Rio's second mission. The player now tests nutrient essentiality:
    growth can collapse when a required medium component is unavailable.
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

        self.mission17 = '17' in self.missions_activated

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
            title='Mission 17',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 17 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 17: Essential Medium Component.

            Mission 16 showed that a different carbon source can rescue growth.
            This mission adds another idea: some medium components are not optional.

            Cells need more than carbon. They also need nutrients used in biomass,
            energy metabolism and cellular building blocks.

            Remove one candidate component at a time and use the Medium Report
            to connect nutrient availability with the growth response.
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
            'Mission 17: Essential Medium Component',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Rio nutrient-essentiality challenge.

            Test how E. coli responds when one important medium component is removed.

            Use {MISSION17_METHOD} with the growth objective.
            Do not use gene knockouts.
            Remove exactly one candidate nutrient at a time.

            Candidate medium components:
            {'  '.join(MISSION17_CANDIDATE_NUTRIENTS)}

            Target concept: {MISSION17_TARGET_NUTRIENT_NAME} availability.
            The report is ready when growth collapses after removing the correct component.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 17 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission17:
            menu.add.button('Deliver Essentiality Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission17, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission17(self):
        clear_mission17_essential_medium_check()
        self.mission17 = True
        if '17' not in self.missions_activated:
            self.missions_activated.insert(0, '17')
        animation_text_save('Mission 17 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission17_essential_medium_check()

        if (not report_data
                or report_data.get('mission_id') != '17'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 17 simulation first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '17' not in self.missions_completed:
                self.missions_completed.insert(0, '17')
            animation_text_save('Congratulations! Mission 17 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('method_correct'):
            animation_text_save('Use FBA for this nutrient-essentiality test.', time=3000)
        elif not report_data.get('objective_correct'):
            animation_text_save('Use the biomass objective to test growth dependence.', time=3000)
        elif report_data.get('knocked_out_genes'):
            animation_text_save('Do not use knockouts. This is a medium challenge.', time=3000)
        elif report_data.get('unexpected_environment_changes'):
            animation_text_save('Too many medium changes. Remove only one candidate nutrient.', time=3000)
        elif not report_data.get('exactly_one_candidate_closed'):
            animation_text_save('Close exactly one candidate nutrient lower bound.', time=3000)
        elif not report_data.get('target_nutrient_closed'):
            animation_text_save(f"That component is not the {MISSION17_TARGET_NUTRIENT_NAME} target yet.", time=3000)
        elif not report_data.get('growth_collapsed'):
            animation_text_save(f"Growth is still above {MISSION17_MAX_GROWTH:.1f}. Check the nutrient test.", time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 17 Essential Medium Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
