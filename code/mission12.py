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
    MISSION12_TARGET_PRODUCT,
    MISSION12_REQUIRED_TRACKED_FLUXES,
    MISSION12_COMPETING_FLUXES,
    MISSION12_MIN_COMPETING_FLUXES,
)


class Mission12_info:
    """Mission 12 — Competing Byproducts.

    Second Dr. Almeida mission. The player must prioritise a target product and
    use Production Flux evidence to compare it with possible competing
    byproducts, without using gene knockouts.
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

        self.mission12 = '12' in self.missions_activated

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
            title='Mission 12',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 12 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 12: Competing Byproducts.

            Mission 11 showed that production fluxes reveal what the model is secreting.
            Now the problem is more focused: one product is desired, but other products can compete for flux.

            Target product: {MISSION12_TARGET_PRODUCT}

            In metabolic engineering, a good analysis does not only ask whether the target is produced.
            It also checks which byproducts appear in the same solution.

            Keep the strain unchanged.
            Use Production Flux evidence to compare the target with competing products.
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
            'Mission 12: Competing Byproducts',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Flux comparison challenge.

            Configure E. coli to prioritise {MISSION12_TARGET_PRODUCT} production.
            Then use Production Flux to support your conclusion with evidence.

            Track the target product and at least {MISSION12_MIN_COMPETING_FLUXES} competing byproducts.

            Possible competing byproducts:
            {'  '.join(MISSION12_COMPETING_FLUXES)}

            Do not use gene knockouts.
            Use New Results to decide when the byproduct comparison is ready.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 12 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission12:
            menu.add.button('Deliver Byproduct Analysis', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission12, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission12(self):
        clear_mission12_byproduct_check()
        self.mission12 = True
        if '12' not in self.missions_activated:
            self.missions_activated.insert(0, '12')
        animation_text_save('Mission 12 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        byproduct_data = load_mission12_byproduct_check()

        if (not byproduct_data
                or byproduct_data.get('mission_id') != '12'
                or byproduct_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 12 simulation first!', time=2500)
            return

        if byproduct_data.get('ready_to_deliver'):
            self.success.play()
            if '12' not in self.missions_completed:
                self.missions_completed.insert(0, '12')
            animation_text_save('Congratulations! Mission 12 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not byproduct_data.get('method_correct'):
            animation_text_save('Use the standard FBA method for this comparison.', time=3000)
        elif not byproduct_data.get('objective_correct'):
            animation_text_save('The objective is not prioritising the requested product yet.', time=3000)
        elif not byproduct_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environment is not suitable for this byproduct comparison yet.', time=3000)
        elif byproduct_data.get('unexpected_environment_changes'):
            animation_text_save('Too many environmental changes. Keep only the key constraint.', time=3000)
        elif byproduct_data.get('knocked_out_genes'):
            animation_text_save('Do not use knockouts in this diagnostic mission.', time=3000)
        elif not byproduct_data.get('target_flux_tracked'):
            animation_text_save('Track the target product in Production Flux.', time=3000)
        elif not byproduct_data.get('competing_fluxes_ready'):
            animation_text_save('Track more competing byproducts before delivering.', time=3000)
        elif not byproduct_data.get('target_flux_positive'):
            animation_text_save('The target product is not being produced enough yet.', time=3000)
        elif not byproduct_data.get('growth_ok'):
            animation_text_save('Growth is too low. The strain is not viable enough.', time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 12 Byproduct Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
