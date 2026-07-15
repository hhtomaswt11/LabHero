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
    MISSION13_BASELINE_METHOD,
    MISSION13_TARGET_METHOD,
    MISSION13_TARGET_PRODUCT,
    MISSION13_TARGET_OBJECTIVE,
    MISSION13_COMPETING_FLUXES,
    MISSION13_MIN_COMPETING_FLUXES,
)


class Mission13_info:
    """Mission 13 — FBA vs pFBA.

    Third Dr. Almeida mission. The player repeats the target/byproduct analysis
    using pFBA, learning that the simulation method can change the flux
    distribution used to explain a metabolic design.
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

        self.mission13 = '13' in self.missions_activated

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
            title='Mission 13',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 13 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 13: FBA vs pFBA.

            {MISSION13_BASELINE_METHOD} focuses on satisfying the selected objective.
            {MISSION13_TARGET_METHOD} adds a second idea: prefer a more parsimonious flux distribution.

            Target product: {MISSION13_TARGET_PRODUCT}

            A method change should not be treated as a cosmetic option.
            It can change how the model distributes flux while pursuing the same target.

            Repeat the previous type of byproduct analysis using {MISSION13_TARGET_METHOD}.
            Keep the strain unchanged and support the diagnosis with production-flux evidence.
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
            'Mission 13: FBA vs pFBA',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Method-comparison challenge.

            Use {MISSION13_TARGET_METHOD} to repeat a controlled analysis for {MISSION13_TARGET_PRODUCT} production.
            Keep the same type of product and byproduct evidence, but change the simulation method.

            Target product objective:
            {MISSION13_TARGET_OBJECTIVE}

            Track the target product and at least {MISSION13_MIN_COMPETING_FLUXES} competing byproducts.

            Possible competing byproducts:
            {'  '.join(MISSION13_COMPETING_FLUXES)}

            Do not use gene knockouts.
            Use New Results to decide when the pFBA comparison is ready.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 13 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission13:
            menu.add.button('Deliver Method Comparison', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission13, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission13(self):
        clear_mission13_method_check()
        self.mission13 = True
        if '13' not in self.missions_activated:
            self.missions_activated.insert(0, '13')
        animation_text_save('Mission 13 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        method_data = load_mission13_method_check()

        if (not method_data
                or method_data.get('mission_id') != '13'
                or method_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 13 simulation first!', time=2500)
            return

        if method_data.get('ready_to_deliver'):
            self.success.play()
            if '13' not in self.missions_completed:
                self.missions_completed.insert(0, '13')
            animation_text_save('Congratulations! Mission 13 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not method_data.get('method_correct'):
            animation_text_save('Change the simulation method to pFBA.', time=3000)
        elif not method_data.get('objective_correct'):
            animation_text_save('The objective is not prioritising the requested product yet.', time=3000)
        elif not method_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environmental constraint is not ready for this comparison.', time=3000)
        elif method_data.get('unexpected_environment_changes'):
            animation_text_save('Too many environmental changes. Keep only the key constraint.', time=3000)
        elif method_data.get('knocked_out_genes'):
            animation_text_save('Do not use knockouts in this method-comparison mission.', time=3000)
        elif not method_data.get('target_flux_tracked'):
            animation_text_save('Track the target product in Production Flux.', time=3000)
        elif not method_data.get('competing_fluxes_ready'):
            animation_text_save('Track more competing byproducts before delivering.', time=3000)
        elif not method_data.get('target_flux_positive'):
            animation_text_save('The target product is not being produced enough yet.', time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 13 Method Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
