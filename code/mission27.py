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
    MISSION27_METHOD,
    MISSION27_GROWTH_OBJECTIVE,
    MISSION27_SWEEP_REACTION,
    MISSION27_SWEEP_BOUND_LABEL,
    MISSION27_SWEEP_VALUES,
    MISSION27_REQUIRED_TRACKED_FLUXES,
    MISSION27_MIN_GROWTH_DROP,
    MISSION27_MAX_FINAL_GROWTH,
    MISSION27_MIN_CHANGED_FLUXES,
)


class Mission27_info:
    """Mission 27 — Glucose Limitation Sweep.

    Second Dr. Luna mission. The player uses Bound Sweep on glucose uptake and
    must interpret a stronger sensitivity pattern: carbon limitation should
    reduce growth and collapse several product/byproduct fluxes.
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

        self.mission27 = '27' in self.missions_activated

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
            title='Mission 27',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 27 Briefing',
            width=1280,
        )

        tracked_flux_text = ', '.join(MISSION27_REQUIRED_TRACKED_FLUXES)
        sweep_values_text = ', '.join(str(value).rstrip('0').rstrip('.') for value in MISSION27_SWEEP_VALUES)

        menu_text.add.label(
            f"""
            Mission 27: Carbon Limitation Sweep.

            Oxygen limitation was only the first step. Now Dr. Luna wants to know
            what happens when the cell progressively loses access to its main
            carbon supply.

            Keep the strain and medium otherwise unchanged. Use a growth-focused
            setup, select a broad product/byproduct evidence panel, and sweep the
            bound that controls uptake of the standard carbon source.

            The correct experiment should reveal more than one number: growth,
            uptake and secretion should all tell the same carbon-limitation story.

            Optional hint: carbon is the material the cell uses to build biomass
            and secrete products. Less carbon available should eventually affect both.
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
            'Mission 27: Carbon Limitation Sweep',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Luna wants a harder sensitivity experiment.

            Question:
            How does E. coli respond when its main carbon supply becomes
            progressively scarce?

            Build a controlled sensitivity test:
            - keep the strain unchanged
            - use a growth-focused simulation
            - do not add unrelated medium changes before the sweep
            - track several fermentation products/byproducts as evidence

            In Bound Sweep Setup, choose the lower bound of the usual carbon-source
            exchange reaction and test it from abundant availability toward no uptake.

            To pass, the trend must show strong carbon limitation: growth should
            fall clearly, the final condition should be close to collapse, and
            several tracked secretions should decrease with the carbon supply.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 27 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission27:
            menu.add.button('Deliver Carbon Sweep', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            if '26' in self.missions_completed:
                menu.add.button('Activate Mission', action=self.activate_mission27, background_color=(50, 100, 100))
            else:
                menu.add.label('Complete Mission 26 before activating this mission.', font_color=(150, 40, 40))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission27(self):
        if '26' not in self.missions_completed:
            self.failed.play()
            animation_text_save('Complete Mission 26 first.', time=2500)
            return

        clear_bound_sweep()
        clear_mission27_bound_sweep_check()
        self.mission27 = True
        if '27' not in self.missions_activated:
            self.missions_activated.insert(0, '27')
        animation_text_save('Mission 27 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission27_bound_sweep_check()

        if (not report_data
                or report_data.get('mission_id') != '27'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 27 carbon-limitation sweep first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '27' not in self.missions_completed:
                self.missions_completed.insert(0, '27')
            animation_text_save('Congratulations! Mission 27 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('clean_base_setup'):
            animation_text_save('Keep the base setup clean: growth objective, no knockouts and no extra medium changes.', time=3000)
        elif not report_data.get('glucose_sweep_selected'):
            animation_text_save('The sweep variable should control uptake of the main carbon source.', time=3000)
        elif not report_data.get('tracking_ready'):
            animation_text_save('Select a broad product/byproduct evidence panel before running the sweep.', time=3000)
        elif not report_data.get('all_points_returned'):
            animation_text_save('The carbon-limitation sweep is missing result points.', time=3000)
        elif not report_data.get('growth_decreased'):
            animation_text_save('Growth did not drop strongly enough across carbon limitation.', time=3000)
        elif not report_data.get('final_growth_low'):
            animation_text_save('The final carbon-limited point should show severe/no growth.', time=3000)
        elif not report_data.get('trend_is_gradual'):
            animation_text_save('Look for a progressive trend, not just one changed row.', time=3000)
        elif not report_data.get('glucose_uptake_decreased'):
            animation_text_save('The tested carbon uptake did not decrease enough across the sweep.', time=3000)
        elif not report_data.get('profile_decreased'):
            animation_text_save('Not enough tracked products/byproducts decreased with the carbon supply.', time=3000)
        else:
            animation_text_save('Almost there. Open the Bound Sweep Report and inspect the carbon-limitation trend.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
