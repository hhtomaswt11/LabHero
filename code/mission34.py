import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from async_menu import run_menu
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION34_CHECK_VERSION,
    MISSION34_CONDITION_LABELS,
    MISSION34_CONDITION_ORDER,
    MISSION34_GENE_NAMES,
    MISSION34_GROWTH_OBJECTIVE,
    MISSION34_METHOD,
    MISSION34_REACTION_GPRS,
    build_mission34_shared_subunit_report_text,
    initialise_mission34_shared_subunit_screen,
    is_mission34_unlocked,
    mission34_answer_matches,
)


class Mission34_info:
    """Mission 34 — Shared-Subunit Equivalence Audit, Dr. Chen."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission34 = '34' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '34', self.missions_completed, mytheme)

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
            title='Mission 34',
            width=1280,
        )

        if not is_mission34_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 34 is locked. Complete Mission 33 before beginning Dr. Chen\'s final equivalence audit.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        run_lines = '\n'.join(
            f'- {MISSION34_CONDITION_LABELS[condition_id]}'
            for condition_id in MISSION34_CONDITION_ORDER
        )
        gene_lines = '\n'.join(
            f'- {gene_id} / {gene_name}'
            for gene_id, gene_name in MISSION34_GENE_NAMES.items()
        )

        hint3 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 34 Hint 3',
            width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION34_METHOD} with objective {MISSION34_GROWTH_OBJECTIVE}. Keep every environmental bound at model default. Record exactly the six highlighted genotypes. No Production Flux selection is required; the report uses visible exchange fluxes and GPR-disabled reactions.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 34 Hint 2',
            width=1280,
        )
        hint2.add.label(
            'Experimental hint: first compare the disabled-reaction sets. Then confirm whether growth, oxygen uptake, formate, pFBA total flux and active-reaction count also match.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 34 Hint 1',
            width=1280,
        )
        hint1.add.label(
            'Conceptual hint: gene count and reaction impact are different. One shared subunit can disable two reactions, while two subunits from the same complex may still disable only one reaction.',
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
            title='Mission 34 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Chen's final experiment tests whether different genotypes can converge on the same reaction-level lesion.

            Controlled protocol:
            - Method: {MISSION34_METHOD}
            - Objective: {MISSION34_GROWTH_OBJECTIVE}
            - Environment: completely model-default and aerobic
            - No unrelated gene or bound changes

            GPR map:
            - PDH: {MISSION34_REACTION_GPRS['PDH']}
            - AKGDH: {MISSION34_REACTION_GPRS['AKGDH']}

            Highlighted genes:
            {gene_lines}

            Record these six visible runs in any order:
            {run_lines}

            Compare b0726 with b0726+b0727, then compare b0116 with b0114+b0726. Begin with the GPR-disabled reaction set rather than the number of deleted genes.
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
            'Mission 34: Shared-Subunit Equivalence Audit',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Determine when different gene knockouts create the same reaction-level metabolic problem.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 34 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission34_shared_subunit_check()
        report_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_options['background_color'] = 'white'
        menu.add.label(
            build_mission34_shared_subunit_report_text(report),
            **report_options,
        )
        menu.add.vertical_margin(20)

        if '34' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission34 or '34' in self.missions_activated:
            self.mission34 = True
            menu.add.label(
                'What is the reaction-level relationship between the b0116 single knockout and the b0114+b0726 double knockout?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Reaction-level relationship: ',
                default='',
                input_underline='_',
                maxchar=28,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission34, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission34(self):
        if not is_mission34_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 33 before starting Mission 34.', time=3000)
            return
        if '34' in self.missions_completed:
            return
        if '34' in self.missions_activated:
            self.mission34 = True
            return

        clear_mission34_shared_subunit_check()
        initialise_mission34_shared_subunit_screen()
        self.mission34 = True
        self.missions_activated.insert(0, '34')
        animation_text_save('Mission 34 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission34_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 33 first!', time=2500)
            return
        if '34' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 34 before delivering a conclusion.', time=2800)
            return

        report = load_mission34_shared_subunit_check()
        if (
            not report
            or report.get('mission_id') != '34'
            or report.get('check_version') != MISSION34_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 34 comparison first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('shared_vs_split_match_supported'):
            self.failed.play()
            animation_text_save('Complete all six controlled pFBA runs first.', time=3000)
            return
        if not mission34_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Classify the reaction-level relationship shown by the matched pair.', time=3000)
            return

        self.success.play()
        if '34' not in self.missions_completed:
            self.missions_completed.insert(0, '34')
        animation_text_save('Congratulations! Mission 34 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
