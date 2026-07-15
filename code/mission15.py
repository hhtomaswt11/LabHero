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
    MISSION15_TARGET_METHOD,
    MISSION15_TARGET_PRODUCT,
    MISSION15_TARGET_OBJECTIVE,
    MISSION15_CANDIDATE_GENES,
    MISSION15_REQUIRED_TRACKED_FLUXES,
)


class Mission15_info:
    """Mission 15 — Final Diagnostic Report.

    Final Dr. Almeida mission. The player produces a complete diagnostic report:
    method, objective, environment, knockout choice and full production-flux evidence.
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

        self.mission15 = '15' in self.missions_activated

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
            title='Mission 15',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 15 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 15: Final Diagnostic Report.

            A good metabolic design is not only a configuration that works once.
            It must be supported by evidence that explains why it works.

            Target product: {MISSION15_TARGET_PRODUCT}

            Bring together the full Dr. Almeida workflow:
            method choice, target objective, environmental reasoning, knockout design and flux evidence.

            The final report should show that the target product dominates the byproduct profile
            while the unwanted route remains controlled.
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
            'Mission 15: Final Diagnostic Report',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Final flux-diagnostic challenge.

            Build a complete diagnostic report for {MISSION15_TARGET_PRODUCT} production.
            Use {MISSION15_TARGET_METHOD}, one useful knockout and full production-flux evidence.

            Target product objective:
            {MISSION15_TARGET_OBJECTIVE}

            Candidate genes:
            {'  '.join(MISSION15_CANDIDATE_GENES)}

            Production Flux evidence required:
            {'  '.join(MISSION15_REQUIRED_TRACKED_FLUXES)}

            Keep the design biologically consistent with the previous diagnostic challenges.
            Use New Results to decide when the final report is ready.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 15 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission15:
            menu.add.button('Deliver Final Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission15, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission15(self):
        clear_mission15_diagnostic_report_check()
        self.mission15 = True
        if '15' not in self.missions_activated:
            self.missions_activated.insert(0, '15')
        animation_text_save('Mission 15 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission15_diagnostic_report_check()

        if (not report_data
                or report_data.get('mission_id') != '15'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 15 simulation first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '15' not in self.missions_completed:
                self.missions_completed.insert(0, '15')
            animation_text_save('Congratulations! Mission 15 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('method_correct'):
            animation_text_save('Use pFBA for the final diagnostic report.', time=3000)
        elif not report_data.get('objective_correct'):
            animation_text_save('The objective is not prioritising the target product yet.', time=3000)
        elif not report_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environmental constraint is not ready yet.', time=3000)
        elif report_data.get('unexpected_environment_changes'):
            animation_text_save('Too many environmental changes. Keep only the key constraint.', time=3000)
        elif not report_data.get('exact_one_knockout'):
            animation_text_save('Use exactly one candidate knockout for the final report.', time=3000)
        elif not report_data.get('target_gene_found'):
            animation_text_save('This knockout does not control the byproduct profile enough.', time=3000)
        elif not report_data.get('required_fluxes_ready'):
            animation_text_save('Track the full production-flux evidence panel.', time=3000)
        elif not report_data.get('target_flux_positive'):
            animation_text_save('The target product is not being produced enough yet.', time=3000)
        elif not report_data.get('unwanted_flux_reduced'):
            animation_text_save('The unwanted byproduct route is still too high.', time=3000)
        elif not report_data.get('target_dominates_byproducts'):
            animation_text_save('The target product does not dominate the byproduct profile yet.', time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 15 Diagnostic Report to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
