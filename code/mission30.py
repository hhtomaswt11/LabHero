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
    MISSION30_CHECK_VERSION,
    MISSION30_METHOD,
    MISSION30_GROWTH_OBJECTIVE,
    MISSION30_GENE_A,
    MISSION30_GENE_B,
    MISSION30_GENE_NAMES,
    MISSION30_SWEEP_VALUES,
    build_mission30_redundancy_threshold_report_text,
    initialise_mission30_redundancy_threshold,
    is_mission30_unlocked,
    mission30_answer_matches,
)


class Mission30_info:
    """Mission 30 — Redundancy Breakdown Threshold, Dr. Li."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission30 = '30' in self.missions_activated

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
            title='Mission 30',
            width=1280,
        )

        if not is_mission30_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 30 is locked. Complete Mission 29 before mapping how oxygen limitation changes the phosphofructokinase redundancy pattern.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        values_text = ', '.join(f'{value:g}' for value in MISSION30_SWEEP_VALUES)

        hint3 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 30 Hint 3',
            width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION30_METHOD} with objective {MISSION30_GROWTH_OBJECTIVE}. Keep the base environment completely default. In Bound Sweep Setup choose Oxygen lower bound and the dedicated PFK redundancy threshold preset ({values_text}). Record wild type, each single knockout, and the exact double knockout. No Production Flux selection is required.',
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
            title='Mission 30 Hint 2',
            width=1280,
        )
        hint2.add.label(
            'Experimental hint: compare every oxygen capacity at the same horizontal position across the four curves. The two single knockouts are controls for preserved isoenzyme redundancy; the double knockout tests what happens after that redundancy has been removed.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 30 Hint 1',
            width=1280,
        )
        hint1.add.label(
            'Conceptual hint: a gene interaction observed in one medium is not automatically stable in another. Watch both numerical growth and solver status. INFEASIBLE is a distinct model outcome and must never be read as a measured growth value of zero.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 30 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Mission 29 showed that the phosphofructokinase pair is tolerated in the default aerobic medium even after both alternatives are removed, although growth falls.

            Dr. Li now wants a matched oxygen-capacity audit to determine whether that conclusion remains stable as respiration becomes progressively restricted.

            Fixed protocol:
            - Method: {MISSION30_METHOD}
            - Objective: {MISSION30_GROWTH_OBJECTIVE}
            - Begin every curve from the completely model-default environment
            - Sweep only the EX_o2_e lower bound with the dedicated values: {values_text}
            - Record four curves in any order:
              1. Wild type
              2. Only {MISSION30_GENE_A} / {MISSION30_GENE_NAMES[MISSION30_GENE_A]} knocked out
              3. Only {MISSION30_GENE_B} / {MISSION30_GENE_NAMES[MISSION30_GENE_B]} knocked out
              4. The exact {MISSION30_GENE_A} + {MISSION30_GENE_B} double knockout

            The report must preserve every feasible measurement and every solver status. Compare the double-knockout trajectory with all three controls and identify the first tested oxygen capacity at which only the double knockout loses feasibility.

            The result is conditional on this model, objective, pair, base medium and tested lower-bound values.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 30: Redundancy Breakdown Threshold',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Build four matched oxygen-response curves and determine when a previously tolerated double knockout changes from a measurable phenotype to a loss of model feasibility.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 30 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission30_redundancy_threshold_check()
        report_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_options['background_color'] = 'white'
        menu.add.label(
            build_mission30_redundancy_threshold_report_text(report),
            **report_options,
        )
        menu.add.vertical_margin(20)

        if '30' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission30 or '30' in self.missions_activated:
            self.mission30 = True
            menu.add.label(
                'Question: At which tested oxygen lower-bound value does the phosphofructokinase double knockout first become infeasible while wild type and both single knockouts remain viable?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Oxygen lower bound: ',
                default='',
                input_underline='_',
                maxchar=80,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission30, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission30(self):
        if not is_mission30_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 29 before starting Mission 30.', time=3000)
            return
        if '30' in self.missions_completed:
            return
        if '30' in self.missions_activated:
            self.mission30 = True
            return

        clear_bound_sweep()
        clear_mission30_redundancy_threshold_check()
        initialise_mission30_redundancy_threshold()
        self.mission30 = True
        self.missions_activated.insert(0, '30')
        animation_text_save('Mission 30 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission30_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 29 first!', time=2500)
            return
        if '30' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 30 before delivering a conclusion.', time=2800)
            return

        report = load_mission30_redundancy_threshold_check()
        if (
            not report
            or report.get('mission_id') != '30'
            or report.get('check_version') != MISSION30_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 30 threshold curves first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('threshold_supported'):
            self.failed.play()
            animation_text_save('Complete all four matched oxygen curves and preserve the solver status at every tested bound before answering.', time=3800)
            return
        if not mission30_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Compare the first INFEASIBLE double-knockout row with all three controls at the same oxygen bound.', time=3600)
            return

        self.success.play()
        if '30' not in self.missions_completed:
            self.missions_completed.insert(0, '30')
        animation_text_save('Congratulations! Mission 30 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
