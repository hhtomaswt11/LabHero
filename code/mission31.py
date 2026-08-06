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
    MISSION31_CHECK_VERSION,
    MISSION31_METHOD,
    MISSION31_GROWTH_OBJECTIVE,
    MISSION31_GENE_A,
    MISSION31_GENE_B,
    MISSION31_GENE_NAMES,
    MISSION31_TARGET_REACTIONS,
    MISSION31_SOURCE_ORDER,
    MISSION31_SOURCE_NAMES,
    build_mission31_environmental_suppression_report_text,
    initialise_mission31_environmental_suppression_matrix,
    is_mission31_unlocked,
    mission31_answer_matches,
)


class Mission31_info:
    """Mission 31 — Environmental Suppression Matrix, Dr. Li."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission31 = '31' in self.missions_activated

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
            title='Mission 31',
            width=1280,
        )

        if not is_mission31_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 31 is locked. Complete Mission 30 before beginning Dr. Li\'s final environmental-suppression experiment.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        source_lines = '\n'.join(
            f'- {source_id}: {MISSION31_SOURCE_NAMES[source_id]}'
            for source_id in MISSION31_SOURCE_ORDER
        )

        hint3 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 31 Hint 3',
            width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION31_METHOD} with objective {MISSION31_GROWTH_OBJECTIVE}. Close the lower bound of EX_glc__D_e and open exactly one highlighted replacement source. Keep oxygen and every unrelated bound at model default. For each source, record wild type and the exact {MISSION31_GENE_A} + {MISSION31_GENE_B} double knockout. No Production Flux selection is required.',
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
            title='Mission 31 Hint 2',
            width=1280,
        )
        hint2.add.label(
            'Experimental hint: compare each double knockout only with the wild-type run using the same replacement source. A positive uptake proves that the source enters the model, but it does not prove that biomass production has been rescued.',
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
            title='Mission 31 Hint 1',
            width=1280,
        )
        hint1.add.label(
            'Conceptual hint: synthetic lethality is conditional on the tested environment. Look for a carbon-entry route that restores strong growth even though both aconitase reactions remain disabled by the same double knockout.',
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
            title='Mission 31 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Mission 29 identified {MISSION31_GENE_A} / {MISSION31_GENE_NAMES[MISSION31_GENE_A]} and {MISSION31_GENE_B} / {MISSION31_GENE_NAMES[MISSION31_GENE_B]} as a synthetic-lethal aconitase pair in the default glucose medium.

            Dr. Li now asks whether that classification remains valid when carbon enters the network through a different route.

            Fixed protocol:
            - Method: {MISSION31_METHOD}
            - Objective: {MISSION31_GROWTH_OBJECTIVE}
            - Close glucose uptake
            - Open exactly one replacement source at its standard -10 capacity
            - Keep oxygen and every unrelated environmental bound at model default
            - For each source, record two matched visible runs:
              1. Wild type
              2. Exact {MISSION31_GENE_A} + {MISSION31_GENE_B} double knockout

            Tested replacement sources:
            {source_lines}

            This produces eight visible matrix cells. Compare growth retention, measured source uptake and the GPR-disabled reactions. A feasible growth value of zero is not an INFEASIBLE status, and source uptake alone is not a rescue.

            Identify the tested environment that suppresses the no-growth phenotype while {MISSION31_TARGET_REACTIONS[0]} and {MISSION31_TARGET_REACTIONS[1]} remain disabled.
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
            'Mission 31: Environmental Suppression Matrix',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Test whether a synthetic-lethal aconitase phenotype remains stable across matched replacement-carbon environments.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 31 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission31_environmental_suppression_check()
        report_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_options['background_color'] = 'white'
        menu.add.label(
            build_mission31_environmental_suppression_report_text(report),
            **report_options,
        )
        menu.add.vertical_margin(20)

        if '31' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission31 or '31' in self.missions_activated:
            self.mission31 = True
            menu.add.label(
                'Question: Which tested replacement carbon source suppressed the aconitase no-growth phenotype while ACONTa and ACONTb remained disabled?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Replacement source: ',
                default='',
                input_underline='_',
                maxchar=120,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission31, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission31(self):
        if not is_mission31_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 30 before starting Mission 31.', time=3000)
            return
        if '31' in self.missions_completed:
            return
        if '31' in self.missions_activated:
            self.mission31 = True
            return

        clear_mission31_environmental_suppression_check()
        initialise_mission31_environmental_suppression_matrix()
        self.mission31 = True
        self.missions_activated.insert(0, '31')
        animation_text_save('Mission 31 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission31_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 30 first!', time=2500)
            return
        if '31' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 31 before delivering a conclusion.', time=2800)
            return

        report = load_mission31_environmental_suppression_check()
        if (
            not report
            or report.get('mission_id') != '31'
            or report.get('check_version') != MISSION31_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 31 source matrix first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('unique_suppression_supported'):
            self.failed.play()
            animation_text_save('Complete all eight matched source runs before answering.', time=3200)
            return
        if not mission31_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Compare matched growth, uptake and disabled aconitase reactions.', time=3200)
            return

        self.success.play()
        if '31' not in self.missions_completed:
            self.missions_completed.insert(0, '31')
        animation_text_save('Congratulations! Mission 31 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
