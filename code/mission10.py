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
    MISSION10_TARGET_PRODUCT,
    MISSION10_CANDIDATE_GENES,
    MISSION10_MIN_GROWTH,
    MISSION10_MIN_PRODUCTION_CHANGE,
)


class Mission10_info:
    """Mission 10 — Multi-Knockout Robust Design.

    Final Dr. Nova mission. The player must combine objective selection,
    environmental constraints, production-flux evidence, and two knockouts.
    The exact objective, environmental reaction, and knockout pair are not
    shown in the prompt; the player must iterate using New Results feedback.
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

        self.mission10 = '10' in self.missions_activated

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
            title='Mission 10',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 10 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 10: Multi-Knockout Robust Design.

            This is Dr. Nova's final challenge. Mission 09 showed how one knockout can improve a design.
            Now the problem becomes harder: two knockouts can interact,
            redirect flux, or damage growth.

            Target product: {MISSION10_TARGET_PRODUCT}

            Candidate genes:
            {'  '.join(MISSION10_CANDIDATE_GENES)}

            Robust strain design is not only about finding high production.
            The model must also remain viable, and the result should be
            supported by production-flux evidence.

            Use simulations to compare knockout pairs, environmental constraints
            and product fluxes. Avoid random extra changes and refine your
            design using New Results.
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
            'Mission 10: Multi-Knockout Robust Design',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Final Dr. Nova challenge.

            Build a robust E. coli design for {MISSION10_TARGET_PRODUCT} production.
            Combine objective choice, environmental constraints,
            exactly two knockouts, and production-flux evidence.

            Candidate genes:
            {'  '.join(MISSION10_CANDIDATE_GENES)}

            You are not given the exact objective, environmental reaction,
            fluxes to track, or knockout pair. Find them by testing.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 10 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission10:
            menu.add.button('Deliver Robust Design', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission10, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission10(self):
        self.mission10 = True
        if '10' not in self.missions_activated:
            self.missions_activated.insert(0, '10')
        animation_text_save('Mission 10 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        design_data = load_mission10_robust_design_check()

        if not design_data:
            self.failed.play()
            animation_text_save('Run a Mission 10 simulation first!', time=2500)
            return

        if design_data.get('ready_to_deliver'):
            self.success.play()
            if '10' not in self.missions_completed:
                self.missions_completed.insert(0, '10')
            animation_text_save('Congratulations! Dr. Nova arc completed!', time=3000)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not design_data.get('objective_correct'):
            animation_text_save('The objective is not targeting the requested product yet.', time=3000)
        elif not design_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environment is not fermentation-compatible yet.', time=3000)
        elif design_data.get('unexpected_environment_changes'):
            animation_text_save('Too many environmental changes. Keep only the key constraint.', time=3000)
        elif not design_data.get('tracking_ready'):
            animation_text_save('Evidence is incomplete. Track the target and a competing product flux.', time=3000)
        elif not design_data.get('exactly_two_knockouts'):
            animation_text_save('Use exactly two candidate gene knockouts.', time=3000)
        elif not design_data.get('target_pair_found'):
            animation_text_save('This knockout pair is not robust enough. Test another pair.', time=3000)
        elif not design_data.get('production_improved'):
            animation_text_save('Production did not improve enough. Refine the design.', time=3000)
        elif not design_data.get('growth_ok'):
            animation_text_save('Growth is too low. The strain is not viable enough.', time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 10 Robust Design Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
