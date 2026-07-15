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
    MISSION14_TARGET_METHOD,
    MISSION14_TARGET_PRODUCT,
    MISSION14_UNWANTED_PRODUCT,
    MISSION14_CANDIDATE_GENES,
    MISSION14_REQUIRED_TRACKED_FLUXES,
)


class Mission14_info:
    """Mission 14 — Byproduct Reduction Design.

    Fourth Dr. Almeida mission. The player keeps the target product analysis
    from the previous missions, but now must use one knockout to reduce an
    unwanted competing byproduct while preserving target-product evidence.
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

        self.mission14 = '14' in self.missions_activated

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
            title='Mission 14',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 14 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 14: Byproduct Reduction Design.

            Mission 13 compared methods and showed that flux evidence can reveal side-products.
            Now the challenge is to improve the quality of the design, not just the target flux.

            Target product: {MISSION14_TARGET_PRODUCT}
            Unwanted byproduct: {MISSION14_UNWANTED_PRODUCT}

            In metabolic engineering, a useful strain should favour the desired product
            while limiting routes that waste carbon or create competing products.

            Use exactly one candidate knockout.
            Keep the diagnosis supported by production-flux evidence.
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
            'Mission 14: Byproduct Reduction Design',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Byproduct-reduction challenge.

            Build on the previous {MISSION14_TARGET_METHOD} analysis for {MISSION14_TARGET_PRODUCT} production.
            This time, use exactly one useful knockout to reduce the unwanted byproduct.

            Candidate genes:
            {'  '.join(MISSION14_CANDIDATE_GENES)}

            Production Flux evidence required:
            {'  '.join(MISSION14_REQUIRED_TRACKED_FLUXES)}

            Keep the same type of environmental constraint.
            Use New Results to decide when the reduction design is ready.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 14 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission14:
            menu.add.button('Deliver Reduction Design', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission14, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission14(self):
        clear_mission14_reduction_check()
        self.mission14 = True
        if '14' not in self.missions_activated:
            self.missions_activated.insert(0, '14')
        animation_text_save('Mission 14 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        reduction_data = load_mission14_reduction_check()

        if (not reduction_data
                or reduction_data.get('mission_id') != '14'
                or reduction_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 14 simulation first!', time=2500)
            return

        if reduction_data.get('ready_to_deliver'):
            self.success.play()
            if '14' not in self.missions_completed:
                self.missions_completed.insert(0, '14')
            animation_text_save('Congratulations! Mission 14 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not reduction_data.get('method_correct'):
            animation_text_save('Use pFBA for this reduction analysis.', time=3000)
        elif not reduction_data.get('objective_correct'):
            animation_text_save('The objective is not prioritising the target product yet.', time=3000)
        elif not reduction_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environmental constraint is not ready yet.', time=3000)
        elif reduction_data.get('unexpected_environment_changes'):
            animation_text_save('Too many environmental changes. Keep only the key constraint.', time=3000)
        elif not reduction_data.get('exact_one_knockout'):
            animation_text_save('Use exactly one knockout from the candidate list.', time=3000)
        elif not reduction_data.get('target_gene_found'):
            animation_text_save('This knockout does not reduce the unwanted byproduct enough.', time=3000)
        elif not reduction_data.get('required_fluxes_ready'):
            animation_text_save('Track the target and unwanted product fluxes.', time=3000)
        elif not reduction_data.get('target_flux_positive'):
            animation_text_save('The target product is not being produced enough yet.', time=3000)
        elif not reduction_data.get('unwanted_flux_reduced'):
            animation_text_save('The unwanted byproduct is still too high.', time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 14 Reduction Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
