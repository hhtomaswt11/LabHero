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
    MISSION19_TARGET_METHOD,
    MISSION19_GROWTH_OBJECTIVE,
    MISSION19_TARGET_GENE,
    MISSION19_TARGET_GENE_NAME,
    MISSION19_CANDIDATE_GENES,
    MISSION19_REQUIRED_TRACKED_FLUXES,
    MISSION19_MIN_GROWTH,
)


class Mission19_info:
    """Mission 19 — Perturbation Method Challenge.

    Dr. Rio now introduces lMOMA as a method for studying the response to a
    single-gene perturbation. Unlike FBA/pFBA missions, the focus is not only
    the final optimum, but whether the mutant can still maintain a viable
    metabolic response while the player records pathway evidence.
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

        self.mission19 = '19' in self.missions_activated

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
            title='Mission 19',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 19 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 19: Perturbation Method Challenge.

            FBA asks what the best possible flux distribution can be for a chosen objective.
            lMOMA is useful after a perturbation because it represents a more conservative adjustment.

            In this mission, the perturbation is genetic, not environmental.
            Keep the medium unchanged, use one candidate knockout, and compare pathway evidence.

            Track products connected with central carbon metabolism so the result is not just a growth number.
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
            'Mission 19: Perturbation Method Challenge',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Rio perturbation-method challenge.

            Study how E. coli responds to a single-gene perturbation using {MISSION19_TARGET_METHOD}.

            Use the growth objective:
            {MISSION19_GROWTH_OBJECTIVE}

            Keep the environmental conditions unchanged.

            Candidate genes:
            {'  '.join(MISSION19_CANDIDATE_GENES)}

            Production Flux evidence:
            {'  '.join(MISSION19_REQUIRED_TRACKED_FLUXES)}

            Find the useful perturbation and prove that the mutant response remains viable.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 19 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission19:
            menu.add.button('Deliver Perturbation Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission19, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission19(self):
        clear_mission19_perturbation_check()
        self.mission19 = True
        if '19' not in self.missions_activated:
            self.missions_activated.insert(0, '19')
        animation_text_save('Mission 19 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission19_perturbation_check()

        if (not report_data
                or report_data.get('mission_id') != '19'
                or report_data.get('check_version') != 2):
            self.failed.play()
            animation_text_save('Run a Mission 19 simulation first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '19' not in self.missions_completed:
                self.missions_completed.insert(0, '19')
            animation_text_save('Congratulations! Mission 19 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('method_correct'):
            animation_text_save(f"Use {MISSION19_TARGET_METHOD} for this perturbation-response test.", time=3000)
        elif not report_data.get('objective_correct'):
            animation_text_save('Use the biomass objective to evaluate mutant viability.', time=3000)
        elif report_data.get('environment_changed'):
            animation_text_save('Keep the medium unchanged. This mission isolates the genetic perturbation.', time=3000)
        elif not report_data.get('exact_one_knockout'):
            animation_text_save('Use exactly one candidate gene knockout.', time=3000)
        elif not report_data.get('target_gene_found'):
            animation_text_save('That perturbation is not the useful response yet. Test another candidate gene.', time=3000)
        elif not report_data.get('tracking_ready'):
            animation_text_save('Track the required pathway products in Production Flux.', time=3000)
        elif not report_data.get('growth_ok'):
            animation_text_save(f"The mutant response is not viable enough. Growth must be above {MISSION19_MIN_GROWTH:.1f}.", time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 19 Perturbation Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
