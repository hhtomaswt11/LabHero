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
    MISSION15_CHECK_VERSION,
    MISSION15_TARGET_METHOD,
    MISSION15_TARGET_PRODUCT,
    MISSION15_PRODUCT_OBJECTIVE,
    MISSION15_GROWTH_OBJECTIVE,
    MISSION15_REQUIRED_TRACKED_FLUXES,
    MISSION15_PRODUCT_NAMES,
    build_mission15_viability_report_text,
    initialise_mission15_viability_audit,
    is_mission15_unlocked,
    mission15_answer_matches,
    normalise_mission15_answer,
)


class Mission15_info:
    """Mission 15 — Product–Growth Viability Audit.

    The player compares product-priority and growth-priority pFBA optima while
    keeping strain, medium and exchange evidence fixed.  The written conclusion
    must be derived from the two visible results.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission15 = '15' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '15', self.missions_completed, mytheme)

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
            title='Mission 15',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('15'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 15 is locked. Complete Mission 14 before beginning the final Dr. Almeida audit.',
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
            theme=mytheme, title='Mission 15 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f'Technical hint: use {MISSION15_TARGET_METHOD}, keep all genes active, keep default glucose, close only the lower bound of EX_o2_e, and track ' + ', '.join(MISSION15_REQUIRED_TRACKED_FLUXES) + f'. Record one run with objective {MISSION15_PRODUCT_OBJECTIVE} and one with {MISSION15_GROWTH_OBJECTIVE}.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 15 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: the selected objective must be the only variable that changes. Compare biomass in the product-priority solution with succinate in the growth-priority solution.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 15 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: a high optimum for one reaction does not by itself establish that another biological objective is simultaneously supported.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 15 Briefing', width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Mission 14 showed why a favourable change in one product does not automatically establish a good intervention. Dr. Almeida now wants a final viability audit.

            Build two controlled {MISSION15_TARGET_METHOD} optima under the same anaerobic medium, with all genes active and the same complete exchange panel. In one run prioritise {MISSION15_TARGET_PRODUCT}; in the other prioritise predicted growth. Change only the selected objective.

            Use the two visible solutions to determine what relationship between growth and product formation is supported. Base the final conclusion on the cross-objective fluxes rather than on the objective values alone.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        panel_text = '   '.join(
            f"{MISSION15_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
            for reaction_id in MISSION15_REQUIRED_TRACKED_FLUXES
        )
        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 15: Product–Growth Viability Audit',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Compare product-priority and growth-priority pFBA solutions under one controlled biological setup, then interpret the cross-objective evidence.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Objectives to compare:\n{MISSION15_PRODUCT_OBJECTIVE}   {MISSION15_GROWTH_OBJECTIVE}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=25,
            padding=(5, 0, 0, 35),
        )
        menu.add.label(
            f'Complete target/co-product panel:\n{panel_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=25,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 15 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission15:
            report = load_mission15_diagnostic_report_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '15'
                or report.get('check_version') != MISSION15_CHECK_VERSION
            ):
                report = initialise_mission15_viability_audit()
            menu.add.label(
                build_mission15_viability_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'Evidence-based conclusion: ',
                default='',
                input_underline='_',
                maxchar=80,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission15, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission15(self):
        if not self.player.is_mission_unlocked('15'):
            self.failed.play()
            animation_text_save('Complete Mission 14 before starting Mission 15.', time=3000)
            return
        if '15' in self.missions_completed:
            return
        if '15' in self.missions_activated:
            self.mission15 = True
            return

        clear_mission15_diagnostic_report_check()
        initialise_mission15_viability_audit()
        self.mission15 = True
        self.missions_activated.insert(0, '15')
        animation_text_save('Mission 15 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('15'):
            self.failed.play()
            animation_text_save('Complete Mission 14 first!', time=2500)
            return
        if '15' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 15 before delivering a conclusion.', time=2800)
            return

        report = load_mission15_diagnostic_report_check()
        if (
            not report
            or report.get('mission_id') != '15'
            or report.get('check_version') != MISSION15_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Build the controlled Mission 15 objective comparison first.', time=3000)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            animation_text_save('Record both complete visible optima before answering.', time=3200)
            return
        if normalise_mission15_answer(answer) is None:
            self.failed.play()
            animation_text_save('State the relationship supported by the two controlled optima.', time=3000)
            penalize_wrong_answer(self.player, '15')
            return
        if not mission15_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That conclusion is not consistent with both cross-objective fluxes.', time=3300)
            penalize_wrong_answer(self.player, '15')
            return

        self.success.play()
        if '15' not in self.missions_completed:
            self.missions_completed.insert(0, '15')
        animation_text_save('Congratulations! Mission 15 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()
