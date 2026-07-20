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
    MISSION22_METHOD,
    MISSION22_GROWTH_OBJECTIVE,
    MISSION22_TARGET_PRODUCT,
    MISSION22_TARGET_FLUX,
    MISSION22_TARGET_GENE,
    MISSION22_TARGET_GENE_NAME,
    MISSION22_CANDIDATE_GENES,
    MISSION22_MIN_PRODUCTION_INCREASE,
)


class Mission22_info:
    """Mission 22 — Knockout Comparison.

    Second Dr. Vega mission. The player compares the normal strain with a
    single-gene knockout while tracking ethanol production.
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

        self.mission22 = '22' in self.missions_activated

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
            title='Mission 22',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 22 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Mission 22: Knockout Comparison.

            In Mission 21 you compared two environments. Now compare two strains:
            the normal strain and a strain with one gene disabled.

            Keep the method, objective and environment the same in both runs.
            The only intended change is the gene knockout.

            Use Production Flux to track {MISSION22_TARGET_PRODUCT}
            ({MISSION22_TARGET_FLUX}) in both runs. Then open Compare Runs to
            check whether the knockout increased product secretion while the
            cell still grows.
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
            'Mission 22: Knockout Comparison',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Vega now wants a controlled gene comparison.

            Question:
            Does one candidate knockout increase {MISSION22_TARGET_PRODUCT}
            production compared with the normal strain?

            Run A — baseline strain:
            - Method: {MISSION22_METHOD}
            - Objective: {MISSION22_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: unchanged
            - Production Flux: track {MISSION22_TARGET_FLUX}

            Run B — modified strain:
            - Method: {MISSION22_METHOD}
            - Objective: {MISSION22_GROWTH_OBJECTIVE}
            - Genes: turn off {MISSION22_TARGET_GENE} / {MISSION22_TARGET_GENE_NAME}
            - Environment: unchanged
            - Production Flux: track {MISSION22_TARGET_FLUX}

            Candidate genes:
            {', '.join(MISSION22_CANDIDATE_GENES)}

            After the second simulation, open New Results -> Compare Runs.
            {MISSION22_TARGET_PRODUCT.capitalize()} should increase by at least
            {MISSION22_MIN_PRODUCTION_INCREASE:.1f}.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 22 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission22:
            menu.add.button('Deliver Knockout Comparison', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            if '21' in self.missions_completed:
                menu.add.button('Activate Mission', action=self.activate_mission22, background_color=(50, 100, 100))
            else:
                menu.add.label('Complete Mission 21 before activating this mission.', font_color=(150, 40, 40))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission22(self):
        if '21' not in self.missions_completed:
            self.failed.play()
            animation_text_save('Complete Mission 21 first.', time=2500)
            return

        clear_compare_runs()
        clear_mission22_comparison_check()
        self.mission22 = True
        if '22' not in self.missions_activated:
            self.missions_activated.insert(0, '22')
        animation_text_save('Mission 22 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission22_comparison_check()

        if (not report_data
                or report_data.get('mission_id') != '22'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 22 comparison first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '22' not in self.missions_completed:
                self.missions_completed.insert(0, '22')
            animation_text_save('Congratulations! Mission 22 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('baseline_run_found'):
            animation_text_save('Missing baseline. Run normal FBA, no knockouts, unchanged environment.', time=3000)
        elif not report_data.get('knockout_run_found'):
            animation_text_save(f'Missing knockout run. Turn off only {MISSION22_TARGET_GENE} and run again.', time=3000)
        elif not report_data.get('target_flux_tracked'):
            animation_text_save(f'Track {MISSION22_TARGET_FLUX} in Production Flux for both runs.', time=3000)
        elif not report_data.get('production_increased'):
            animation_text_save('The ethanol increase is not clear enough yet.', time=3000)
        elif not report_data.get('growth_ok'):
            animation_text_save('The knockout design does not remain viable enough.', time=3000)
        else:
            animation_text_save('Almost there. Open Compare Runs and check the knockout comparison.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
