import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from async_menu import run_menu
from simulation import (
    MISSION08_TARGET_PRODUCT,
)


class Mission08_info:
    """Mission 08 — Objective Under Constraints.

    Second Dr. Nova mission. The player must discover which objective and
    environmental constraint make sense for lactate production, instead of
    being given the exact configuration directly.
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

        self.mission08 = '08' in self.missions_activated

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
            title='Mission 08',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 08 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 08: Objective Under Constraints.

            Mission 07 showed that the objective function changes what the model tries to optimise.
            This mission adds a second idea: constraints define what the model is allowed to do.

            Target product: lactate

            In constraint-based modelling, environmental limits can change the possible flux distribution.
            Nutrient availability, oxygen availability and reaction limits all shape the result.

            Lactate is connected with fermentative metabolism.
            Think about how cells adapt when respiration becomes limited, then compare your simulations.

            Do not solve this as a genetic problem.
            Keep the strain unchanged and focus on objective choice, environmental constraints and product formation.
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
            'Mission 08: Objective Under Constraints',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            A production objective is not enough by itself.

            Configure E. coli so {MISSION08_TARGET_PRODUCT} becomes the target product under a
            biologically meaningful constraint.

            Keep the strain unchanged. Explore how objective choice and environment interact,
            then deliver your result when the constrained setup is ready.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 08 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission08:
            menu.add.button('Deliver Constraint Results', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission08, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission08(self):
        self.mission08 = True
        if '08' not in self.missions_activated:
            self.missions_activated.insert(0, '08')
        animation_text_save('Mission 08 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        objective_data = load_mission08_constraint_check()

        if not objective_data:
            self.failed.play()
            animation_text_save('Run a Mission 08 simulation first!', time=2500)
            return

        if objective_data.get('ready_to_deliver'):
            self.success.play()
            if '08' not in self.missions_completed:
                self.missions_completed.insert(0, '08')
            animation_text_save('Congratulations! Mission Completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if objective_data.get('knocked_out_genes'):
            animation_text_save('This mission uses objective and environment only. Reset the genes.', time=3000)
        elif objective_data.get('unexpected_environment_changes'):
            animation_text_save('You changed too many environmental conditions. Simplify the setup.', time=3000)
        elif not objective_data.get('objective_correct'):
            animation_text_save('The objective is not targeting the requested product yet.', time=3000)
        elif not objective_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environment is not in the right fermentation context yet.', time=3000)
        else:
            animation_text_save('Keep testing until the constrained production check is ready.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback

    async def update(self):
        self.input()
        await self.setup()
