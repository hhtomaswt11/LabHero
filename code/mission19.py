import pygame
import pygame_menu

from answer_penalty import penalize_wrong_answer

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from async_menu import run_menu
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION19_CHECK_VERSION,
    MISSION19_BASELINE_METHOD,
    MISSION19_TARGET_METHOD,
    MISSION19_GROWTH_OBJECTIVE,
    MISSION19_TARGET_GENE,
    MISSION19_TARGET_GENE_NAME,
    MISSION19_EXPECTED_DISABLED_REACTIONS,
    MISSION19_REQUIRED_TRACKED_FLUXES,
    LMOMA_DISPLAY_NAME,
    build_mission19_method_comparison_report_text,
    initialise_mission19_method_comparison,
    is_mission19_unlocked,
    mission19_answer_matches,
    normalise_mission19_answer,
)


class Mission19_info:
    """Mission 19 — Re-optimisation vs Minimal Adjustment."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission19 = '19' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '19', self.missions_completed, mytheme)

        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 19',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('19'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 19 is locked. Complete Mission 18 before beginning the method-comparison experiment.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 19 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f'Technical hint: record a wild-type {MISSION19_BASELINE_METHOD} baseline, then use the single knockout {MISSION19_TARGET_GENE} / {MISSION19_TARGET_GENE_NAME} under FBA and {LMOMA_DISPLAY_NAME}. Keep the default medium, biomass objective and the full product panel unchanged.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 19 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: isolate method choice. The two mutant runs must use the same gene, objective, medium and tracked fluxes; only FBA versus Linear MOMA (lMOMA) may change.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 19 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: FBA re-optimises the selected objective after a perturbation. Linear MOMA (lMOMA) instead minimises total absolute flux adjustment from a reference state, so its method score is not biomass.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 19 Briefing', width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Rio now wants a controlled comparison of two post-perturbation modelling questions.

            Phase A — wild-type reference:
            Use {MISSION19_BASELINE_METHOD}, the biomass objective, every gene active, the completely default medium and the complete product/byproduct panel.

            Phase B — re-optimised mutant:
            Disable only {MISSION19_TARGET_GENE} / {MISSION19_TARGET_GENE_NAME}. Keep every other setting unchanged and use FBA.

            Phase C — minimally adjusted mutant:
            Repeat the same knockout and setup with {LMOMA_DISPLAY_NAME}. The visible report must include both predicted growth rate and the lMOMA adjustment score. The adjustment score is not the predicted growth rate.

            Compare the two mutant biomass predictions and answer with one method name. No hidden simulation is used.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label('Mission 19: Re-optimisation vs Minimal Adjustment', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            'Record one wild-type reference and compare the same viable knockout under FBA and Linear MOMA (lMOMA) while changing only the simulation method.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Target knockout: {MISSION19_TARGET_GENE} / {MISSION19_TARGET_GENE_NAME}\nGPR-disabled reaction: {", ".join(MISSION19_EXPECTED_DISABLED_REACTIONS)}\nProduction Flux panel: {", ".join(MISSION19_REQUIRED_TRACKED_FLUXES)}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=24,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 19 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission19:
            report = load_mission19_perturbation_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '19'
                or report.get('check_version') != MISSION19_CHECK_VERSION
            ):
                report = initialise_mission19_method_comparison()
            menu.add.label(
                build_mission19_method_comparison_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.label(
                'Question: Which method predicted the lower viable biomass response for the same b0728 knockout?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Method: ',
                default='',
                input_underline='_',
                maxchar=50,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission19, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission19(self):
        if not self.player.is_mission_unlocked('19'):
            self.failed.play()
            animation_text_save('Complete Mission 18 before starting Mission 19.', time=3000)
            return
        if '19' in self.missions_completed:
            return
        if '19' in self.missions_activated:
            self.mission19 = True
            return

        clear_mission19_perturbation_check()
        initialise_mission19_method_comparison()
        self.mission19 = True
        self.missions_activated.insert(0, '19')
        animation_text_save('Mission 19 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('19'):
            self.failed.play()
            animation_text_save('Complete Mission 18 first!', time=2500)
            return
        if '19' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 19 before delivering a conclusion.', time=2800)
            return

        report = load_mission19_perturbation_check()
        if (
            not report
            or report.get('mission_id') != '19'
            or report.get('check_version') != MISSION19_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the Mission 19 reference and method comparison first.', time=3000)
            return
        if not report.get('baseline_ready'):
            self.failed.play()
            animation_text_save('Record the wild-type FBA baseline first.', time=3000)
            return
        if not report.get('comparison_ready'):
            self.failed.play()
            animation_text_save('Record both b0728 mutant runs: FBA and lMOMA.', time=3000)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible comparison does not support one lower viable method response.', time=3000)
            return
        if len(normalise_mission19_answer(answer)) != 1:
            self.failed.play()
            animation_text_save('Enter exactly one simulation method.', time=2800)
            penalize_wrong_answer(self.player, '19')
            return
        if not mission19_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That method is not supported by the recorded biomass comparison.', time=3000)
            penalize_wrong_answer(self.player, '19')
            return

        self.success.play()
        if '19' not in self.missions_completed:
            self.missions_completed.insert(0, '19')
        animation_text_save('Congratulations! Mission 19 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
