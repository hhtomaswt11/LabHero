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
    MISSION26_CHECK_VERSION,
    MISSION26_METHOD,
    MISSION26_GROWTH_OBJECTIVE,
    MISSION26_TARGET_GENE,
    MISSION26_TARGET_GENE_NAME,
    MISSION26_SWEEP_REACTION,
    MISSION26_SWEEP_VALUES,
    build_mission26_interaction_report_text,
    initialise_mission26_interaction_curves,
    is_mission26_unlocked,
    mission26_answer_matches,
)


class Mission26_info:
    """Mission 26 — Genotype-Environment Interaction Curve."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission26 = '26' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '26', self.missions_completed, mytheme)

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
            title='Mission 26',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('26'):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 26 is locked. Complete Mission 25 before beginning Dr. Smith's second experiment.",
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
            theme=mytheme, title='Mission 26 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f"Technical hint: use {MISSION26_METHOD} with objective {MISSION26_GROWTH_OBJECTIVE}. Keep the base environment completely default. In Bound Sweep Setup choose the lower bound of {MISSION26_SWEEP_REACTION} and values "
            + ', '.join(f'{value:g}' for value in MISSION26_SWEEP_VALUES)
            + f". Run the curve once with every gene active and once with only {MISSION26_TARGET_GENE} / {MISSION26_TARGET_GENE_NAME} knocked out.",
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 26 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: use identical oxygen lower-bound values for both genotypes. Match the rows by bound and compare knockout-to-wild-type growth retention at each point, rather than comparing only the two endpoints.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 26 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: a genotype-environment interaction curve can distinguish a gradual defect from a threshold. Look for the tested oxygen capacity where the mutant response separates sharply from the matched wild-type response.',
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
            title='Mission 26 Briefing',
            width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Smith wants to extend the Mission 25 endpoint matrix into two matched response curves.

            Construct one oxygen-capacity sweep for wild type and one for the highlighted {MISSION26_TARGET_GENE} / {MISSION26_TARGET_GENE_NAME} knockout.

            Controlled protocol:
            - Method: {MISSION26_METHOD}
            - Objective: {MISSION26_GROWTH_OBJECTIVE}
            - Base environment: every bound at model default before the sweep
            - Sweep variable: {MISSION26_SWEEP_REACTION} lower bound
            - Values: {', '.join(f'{value:g}' for value in MISSION26_SWEEP_VALUES)}
            - Genotypes: all genes active, then only the highlighted gene knocked out

            The first oxygen capacity is intentionally non-binding. The remaining values progressively tighten uptake until it is completely blocked. Every row must contain numeric growth, glucose uptake, oxygen uptake and FBA diagnostics from the visible Bound Sweep.

            Compare the two curves at matched bounds. Submit the tested lower-bound value where knockout growth collapses while the corresponding wild type remains viable.
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
            'Mission 26: Genotype-Environment Interaction Curve',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            f'Compare matched oxygen-response curves for wild type and {MISSION26_TARGET_GENE} / {MISSION26_TARGET_GENE_NAME} knockout.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 26 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission26_bound_sweep_check()
        report_label_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_label_options['background_color'] = 'white'
        menu.add.label(
            build_mission26_interaction_report_text(report),
            **report_label_options,
        )
        menu.add.vertical_margin(20)

        if '26' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission26 or '26' in self.missions_activated:
            self.mission26 = True
            menu.add.label(
                'Question: At which tested oxygen lower-bound value does knockout growth collapse while wild-type growth remains viable?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Lower-bound conclusion: ',
                default='',
                input_underline='_',
                maxchar=100,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission26, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission26(self):
        if not self.player.is_mission_unlocked('26'):
            self.failed.play()
            animation_text_save('Complete Mission 25 before starting Mission 26.', time=3000)
            return
        if '26' in self.missions_completed:
            return
        if '26' in self.missions_activated:
            self.mission26 = True
            return

        clear_bound_sweep()
        clear_mission26_bound_sweep_check()
        initialise_mission26_interaction_curves()
        self.mission26 = True
        self.missions_activated.insert(0, '26')
        animation_text_save('Mission 26 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('26'):
            self.failed.play()
            animation_text_save('Complete Mission 25 first!', time=2500)
            return
        if '26' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 26 before delivering a conclusion.', time=2800)
            return

        report = load_mission26_bound_sweep_check()
        if (
            not report
            or report.get('mission_id') != '26'
            or report.get('check_version') != MISSION26_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 26 curves first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('interaction_threshold_supported'):
            self.failed.play()
            animation_text_save('Complete both matched oxygen curves before answering.', time=3000)
            return
        if not mission26_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recompare matched wild-type and knockout growth at every tested lower bound.', time=3300)
            penalize_wrong_answer(self.player, '26')
            return

        self.success.play()
        if '26' not in self.missions_completed:
            self.missions_completed.insert(0, '26')
        animation_text_save('Congratulations! Mission 26 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
