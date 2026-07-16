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
    MISSION20_TARGET_METHOD,
    MISSION20_GROWTH_OBJECTIVE,
    MISSION20_BLOCKED_CARBON_SOURCE,
    MISSION20_ALTERNATIVE_CARBON_SOURCE,
    MISSION20_EXPORT_BOTTLENECK,
    MISSION20_EXPORT_BOTTLENECK_NAME,
    MISSION20_REQUIRED_TRACKED_FLUXES,
    MISSION20_REQUIRED_ESSENTIAL_UPTAKES,
    MISSION20_MIN_GROWTH,
)


class Mission20_info:
    """Mission 20 — Final Medium Robustness Report.

    Final Dr. Rio mission. The player must combine method choice, medium
    engineering, exchange-bound stress and flux evidence into a compact
    robustness report.
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

        self.mission20 = '20' in self.missions_activated

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
            title='Mission 20',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 20 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 20: Final Medium Robustness Report.

            A metabolic design should not be judged only by one objective value.
            It should also show which compounds enter the model and which products leave it.

            This final Rio challenge combines method choice, medium changes,
            exchange-bound stress and flux evidence.

            Use the Medium Report to inspect uptake from the environment.
            Use Production Flux to inspect exported products and byproducts.
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
            'Mission 20: Final Medium Robustness Report',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Rio final robustness challenge.

            Build a viable medium design under exchange-bound stress and justify it
            using both uptake evidence and production-flux evidence.

            Use {MISSION20_TARGET_METHOD} with the growth objective.
            Keep the strain unchanged.

            Original carbon source to remove:
            {MISSION20_BLOCKED_CARBON_SOURCE}

            Alternative carbon source:
            {MISSION20_ALTERNATIVE_CARBON_SOURCE}

            Export bottleneck target:
            {MISSION20_EXPORT_BOTTLENECK_NAME} ({MISSION20_EXPORT_BOTTLENECK})

            Essential uptake evidence:
            {'  '.join(MISSION20_REQUIRED_ESSENTIAL_UPTAKES)}

            Required Production Flux evidence:
            {'  '.join(MISSION20_REQUIRED_TRACKED_FLUXES)}
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 20 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission20:
            menu.add.button('Deliver Robustness Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission20, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission20(self):
        clear_mission20_robustness_report_check()
        self.mission20 = True
        if '20' not in self.missions_activated:
            self.missions_activated.insert(0, '20')
        animation_text_save('Mission 20 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission20_robustness_report_check()

        if (not report_data
                or report_data.get('mission_id') != '20'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 20 simulation first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '20' not in self.missions_completed:
                self.missions_completed.insert(0, '20')
            animation_text_save('Congratulations! Mission 20 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('method_correct'):
            animation_text_save(f"Use {MISSION20_TARGET_METHOD} for the final robustness report.", time=3000)
        elif not report_data.get('objective_correct'):
            animation_text_save('Use the biomass objective to evaluate viability.', time=3000)
        elif report_data.get('knocked_out_genes'):
            animation_text_save('Keep the strain unchanged. This is a medium robustness challenge.', time=3000)
        elif not report_data.get('glucose_lower_bound_closed'):
            animation_text_save('The original carbon source is still available.', time=3000)
        elif not report_data.get('pyruvate_lower_bound_open'):
            animation_text_save('The alternative carbon source is not available yet.', time=3000)
        elif not report_data.get('acetate_upper_bound_closed'):
            animation_text_save('Create the export stress by constraining the acetate upper bound.', time=3000)
        elif report_data.get('unexpected_environment_changes'):
            animation_text_save('Too many medium changes. Keep the robustness design controlled.', time=3000)
        elif not report_data.get('tracking_ready'):
            animation_text_save('Track the full byproduct panel in Production Flux.', time=3000)
        elif not report_data.get('pyruvate_uptake_detected'):
            animation_text_save('Pyruvate is selected but not being consumed enough yet.', time=3000)
        elif not report_data.get('essential_uptake_ready'):
            animation_text_save('The Medium Report is missing essential uptake evidence.', time=3000)
        elif not report_data.get('acetate_export_blocked'):
            animation_text_save('Acetate export is still not constrained enough.', time=3000)
        elif not report_data.get('growth_ok'):
            animation_text_save(f"Growth is below {MISSION20_MIN_GROWTH:.1f}. The design is not robust enough.", time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 20 Robustness Report to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
