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
    MISSION18_METHOD,
    MISSION18_GROWTH_OBJECTIVE,
    MISSION18_BLOCKED_CARBON_SOURCE,
    MISSION18_ALTERNATIVE_CARBON_SOURCE,
    MISSION18_EXPORT_BOTTLENECK,
    MISSION18_EXPORT_BOTTLENECK_NAME,
    MISSION18_REQUIRED_TRACKED_FLUXES,
    MISSION18_MIN_GROWTH,
)


class Mission18_info:
    """Mission 18 — Export Bottleneck.

    Dr. Rio's third mission. The player now uses exchange upper bounds,
    learning that environmental constraints can limit secretion/export, not
    only uptake/import.
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

        self.mission18 = '18' in self.missions_activated

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
            title='Mission 18',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 18 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 18: Export Bottleneck.

            Previous Rio missions focused on what the model imports from the medium.
            Now you will test the other side of exchange reactions: secretion.

            In exchange reactions, lower bounds often control uptake.
            Upper bounds can restrict export, creating a bottleneck for products or byproducts.

            Use both the Medium Report and Production Flux evidence.
            The goal is to show that the model remains viable while a byproduct export route is constrained.
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
            'Mission 18: Export Bottleneck',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Rio exchange-bound challenge.

            Build a controlled medium where E. coli uses an alternative carbon source
            while an unwanted export route is constrained.

            Use {MISSION18_METHOD} with the growth objective.
            Keep the strain unchanged.

            Original carbon source to remove:
            {MISSION18_BLOCKED_CARBON_SOURCE}

            Alternative carbon source to test:
            {MISSION18_ALTERNATIVE_CARBON_SOURCE}

            Export bottleneck target:
            {MISSION18_EXPORT_BOTTLENECK_NAME} ({MISSION18_EXPORT_BOTTLENECK})

            Required Production Flux evidence:
            {'  '.join(MISSION18_REQUIRED_TRACKED_FLUXES)}
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 18 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission18:
            menu.add.button('Deliver Bottleneck Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission18, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission18(self):
        clear_mission18_export_bottleneck_check()
        self.mission18 = True
        if '18' not in self.missions_activated:
            self.missions_activated.insert(0, '18')
        animation_text_save('Mission 18 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission18_export_bottleneck_check()

        if (not report_data
                or report_data.get('mission_id') != '18'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 18 simulation first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '18' not in self.missions_completed:
                self.missions_completed.insert(0, '18')
            animation_text_save('Congratulations! Mission 18 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('method_correct'):
            animation_text_save('Use FBA for this export-bottleneck test.', time=3000)
        elif not report_data.get('objective_correct'):
            animation_text_save('Use the biomass objective to test viability.', time=3000)
        elif report_data.get('knocked_out_genes'):
            animation_text_save('Do not use knockouts. This is an exchange-bound challenge.', time=3000)
        elif not report_data.get('glucose_lower_bound_closed'):
            animation_text_save('The original carbon source is still available.', time=3000)
        elif not report_data.get('pyruvate_lower_bound_open'):
            animation_text_save('The alternative carbon source is not available yet.', time=3000)
        elif not report_data.get('acetate_upper_bound_closed'):
            animation_text_save('Create the export bottleneck by constraining the acetate upper bound.', time=3000)
        elif report_data.get('unexpected_environment_changes'):
            animation_text_save('Too many medium changes. Keep this design controlled.', time=3000)
        elif not report_data.get('tracking_ready'):
            animation_text_save('Track acetate and the competing products in Production Flux.', time=3000)
        elif not report_data.get('pyruvate_uptake_detected'):
            animation_text_save('Pyruvate is selected but not being consumed enough yet.', time=3000)
        elif not report_data.get('acetate_export_blocked'):
            animation_text_save('Acetate export is still not constrained enough.', time=3000)
        elif not report_data.get('growth_ok'):
            animation_text_save(f"Growth is below {MISSION18_MIN_GROWTH:.1f}. Keep the design viable.", time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 18 Export Bottleneck Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
