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
    MISSION09_TARGET_PRODUCT,
    MISSION09_CANDIDATE_GENES,
    MISSION09_MIN_GROWTH,
    MISSION09_MIN_PRODUCTION_CHANGE,
)


class Mission09_info:
    """Mission 09 — Integrated Strain Design.

    Third Dr. Nova mission. It combines objective choice, environmental
    constraints, and a single knockout. The prompt intentionally gives only
    the target and design constraints; the player must discover the exact
    configuration through simulation feedback.
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

        self.mission09 = '09' in self.missions_activated

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
            title='Mission 09',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 09 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 09: Integrated Strain Design.

            Mission 07 focused on objective choice.
            Mission 08 showed that constraints can change what the model can do.

            Now you must combine objective choice, environment and one genetic intervention
            into a single strain-design strategy.

            Target product: {MISSION09_TARGET_PRODUCT}

            In metabolic engineering, a useful knockout is not simply a gene that damages growth.
            It should redirect flux toward the desired product while keeping the strain viable.

            Use the candidate genes as your search space.
            Compare simulations carefully and let New Results guide your next test.
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
            'Mission 09: Integrated Strain Design',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Integrated strain-design challenge.

            Design an E. coli setup that targets {MISSION09_TARGET_PRODUCT} production,
            uses a fermentation-compatible environment, and includes exactly one useful knockout.

            Candidate genes:
            {'  '.join(MISSION09_CANDIDATE_GENES)}

            The solution must improve production without killing growth.
            You are not given the exact objective, environmental reaction, or gene.
            Find them by testing.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 09 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission09:
            menu.add.button('Deliver Design Results', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission09, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission09(self):
        self.mission09 = True
        if '09' not in self.missions_activated:
            self.missions_activated.insert(0, '09')
        animation_text_save('Mission 09 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        design_data = load_mission09_design_check()

        if not design_data:
            self.failed.play()
            animation_text_save('Run a Mission 09 simulation first!', time=2500)
            return

        if design_data.get('ready_to_deliver'):
            self.success.play()
            if '09' not in self.missions_completed:
                self.missions_completed.insert(0, '09')
            animation_text_save('Congratulations! Mission Completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not design_data.get('objective_correct'):
            animation_text_save('The objective is not targeting the requested product yet.', time=3000)
        elif not design_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environment is not fermentation-compatible yet.', time=3000)
        elif design_data.get('unexpected_environment_changes'):
            animation_text_save('Too many environmental changes. Keep only the key constraint.', time=3000)
        elif not design_data.get('single_knockout'):
            animation_text_save('Use exactly one candidate gene knockout.', time=3000)
        elif not design_data.get('production_improved'):
            animation_text_save('Production did not improve enough. Try another candidate gene.', time=3000)
        elif not design_data.get('growth_ok'):
            animation_text_save('Growth is too low. The strain is not viable enough.', time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 09 Design Check to refine the setup.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
