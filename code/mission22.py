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
    MISSION22_CHECK_VERSION,
    MISSION22_METHOD,
    MISSION22_GROWTH_OBJECTIVE,
    MISSION22_OXYGEN_REACTION,
    MISSION22_ENVIRONMENTAL_EXPORT,
    MISSION22_TARGET_GENES,
    MISSION22_TARGET_GENE_NAMES,
    MISSION22_EXPECTED_DISABLED_REACTIONS,
    MISSION22_REQUIRED_TRACKED_FLUXES,
    build_mission22_phenotype_equivalence_report_text,
    initialise_mission22_phenotype_equivalence_audit,
    is_mission22_unlocked,
    mission22_answer_matches,
    normalise_mission22_answer,
)


class Mission22_info:
    """Mission 22 — Phenotype Equivalence Audit.

    Second and final Dr. Vega mission.  Mission 21 established an
    export-bound change; this mission compares two different mechanisms under
    one controlled phenotype panel and determines how many recorded outputs
    distinguish them beyond numerical tolerance.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission22 = '22' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '22', self.missions_completed, mytheme)

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
            title='Mission 22',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('22'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 22 is locked. Complete Mission 21 before beginning Dr. Vega\'s final audit.',
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
            theme=mytheme, title='Mission 22 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f'Technical hint: use {MISSION22_METHOD}, objective {MISSION22_GROWTH_OBJECTIVE}, model-default glucose and close {MISSION22_OXYGEN_REACTION} uptake in both runs. Track ' + ', '.join(MISSION22_REQUIRED_TRACKED_FLUXES) + f'. For the environmental run, keep all genes active and close only the upper bound of {MISSION22_ENVIRONMENTAL_EXPORT}. For the genetic run, restore that upper bound and disable exactly ' + ' + '.join(MISSION22_TARGET_GENES) + '.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 22 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: compare genetic minus environmental values for growth, glucose uptake, oxygen uptake and every tracked secretion. Count an output only when the absolute difference exceeds the tolerance shown by the mission report.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 22 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: different interventions can act through different mechanisms yet remain indistinguishable under a limited observed phenotype panel. Matching outputs do not prove matching mechanisms.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 22 Briefing',
            width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Vega's final task compares two mechanisms under one shared protocol.

            Shared setup:
            Use {MISSION22_METHOD}, the biomass objective, model-default glucose, closed oxygen uptake and the complete product/byproduct panel. Keep every unrelated bound at its model default.

            Environmental intervention:
            Keep every gene active and close the upper bound of {MISSION22_ENVIRONMENTAL_EXPORT}.

            Genetic intervention:
            Restore the acetate upper bound to its model default and disable exactly {MISSION22_TARGET_GENES[0]} / {MISSION22_TARGET_GENE_NAMES[MISSION22_TARGET_GENES[0]]} plus {MISSION22_TARGET_GENES[1]} / {MISSION22_TARGET_GENE_NAMES[MISSION22_TARGET_GENES[1]]}. The complete GPR must report {MISSION22_EXPECTED_DISABLED_REACTIONS[0]} as disabled.

            Record both visible runs in any order. Count only biomass, glucose uptake, oxygen uptake and the five tracked secretions. The intervention settings and GPR-disabled reaction labels identify the mechanisms; they are not phenotype outputs. Submit only the number of counted outputs that differ beyond tolerance.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 22: Phenotype Equivalence Audit',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Compare an environmental intervention with a GPR-based genetic intervention and determine whether the recorded phenotype panel distinguishes them.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Controlled factors:\nOxygen uptake: {MISSION22_OXYGEN_REACTION} lower bound closed in both runs\nEnvironmental mechanism: {MISSION22_ENVIRONMENTAL_EXPORT} upper bound closed; genes active\nGenetic mechanism: {" + ".join(MISSION22_TARGET_GENES)} disabled; acetate upper bound default\nProduction Flux panel: {", ".join(MISSION22_REQUIRED_TRACKED_FLUXES)}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=24,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 22 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission22:
            report = load_mission22_comparison_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '22'
                or report.get('check_version') != MISSION22_CHECK_VERSION
            ):
                report = initialise_mission22_phenotype_equivalence_audit()
            menu.add.label(
                build_mission22_phenotype_equivalence_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.label(
                'Question: How many recorded phenotype outputs differed beyond tolerance between the environmental and genetic interventions?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Different outputs: ',
                default='',
                input_underline='_',
                maxchar=40,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission22, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission22(self):
        if not self.player.is_mission_unlocked('22'):
            self.failed.play()
            animation_text_save('Complete Mission 21 before starting Mission 22.', time=3000)
            return
        if '22' in self.missions_completed:
            return
        if '22' in self.missions_activated:
            self.mission22 = True
            return

        clear_compare_runs()
        clear_mission22_comparison_check()
        initialise_mission22_phenotype_equivalence_audit()
        self.mission22 = True
        self.missions_activated.insert(0, '22')
        animation_text_save('Mission 22 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('22'):
            self.failed.play()
            animation_text_save('Complete Mission 21 first!', time=2500)
            return
        if '22' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 22 before delivering a conclusion.', time=2800)
            return

        report = load_mission22_comparison_check()
        if (
            not report
            or report.get('mission_id') != '22'
            or report.get('check_version') != MISSION22_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the two current-format Mission 22 runs first.', time=3000)
            return
        if not report.get('all_runs_recorded'):
            self.failed.play()
            animation_text_save('Record both the environmental and genetic interventions.', time=3000)
            return
        if not report.get('same_base_protocol'):
            self.failed.play()
            animation_text_save('The two runs do not preserve the shared controlled protocol.', time=3000)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible outputs do not support the required equivalence audit yet.', time=3000)
            return
        if normalise_mission22_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter one unambiguous numerical count only.', time=2800)
            penalize_wrong_answer(self.player, '22')
            return
        if not mission22_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That count is not supported by the recorded output differences.', time=3000)
            penalize_wrong_answer(self.player, '22')
            return

        self.success.play()
        if '22' not in self.missions_completed:
            self.missions_completed.insert(0, '22')
        animation_text_save('Congratulations! Mission 22 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
