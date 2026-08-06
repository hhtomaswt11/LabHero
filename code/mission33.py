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
    MISSION33_CHECK_VERSION,
    MISSION33_CONTEXT_LABELS,
    MISSION33_CONTEXT_ORDER,
    MISSION33_GROWTH_OBJECTIVE,
    MISSION33_MUTANT_METHOD,
    MISSION33_REFERENCE_METHOD,
    MISSION33_RUN_LABELS,
    MISSION33_RUN_ORDER,
    MISSION33_TARGET_GENES,
    MISSION33_TARGET_REACTION,
    ROOM_DEFAULT_DELTA,
    ROOM_DEFAULT_EPSILON,
    ROOM_DEFAULT_LINEAR,
    build_mission33_reference_adjustment_report_text,
    initialise_mission33_reference_adjustment_screen,
    is_mission33_unlocked,
    mission33_answer_matches,
)


class Mission33_info:
    """Mission 33 — Reference-State Adjustment Footprint, Dr. Chen."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission33 = '33' in self.missions_activated

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
            title='Mission 33',
            width=1280,
        )

        if not is_mission33_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 33 is locked. Complete Mission 32 before beginning the ROOM reference-state experiment.',
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
            f'- {MISSION33_RUN_LABELS[run_id]}'
            for run_id in MISSION33_RUN_ORDER
        )
        context_lines = '\n'.join(
            f'- {MISSION33_CONTEXT_LABELS[context_id]}'
            for context_id in MISSION33_CONTEXT_ORDER
        )

        hint3 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 33 Hint 3',
            width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION33_REFERENCE_METHOD} with all genes active for each reference. Use {MISSION33_MUTANT_METHOD} with exactly {MISSION33_TARGET_GENES[0]} + {MISSION33_TARGET_GENES[1]} for each mutant. Keep objective {MISSION33_GROWTH_OBJECTIVE}. The oxygen-closed context changes only the EX_o2_e lower bound. No Production Flux selection is required.',
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
            title='Mission 33 Hint 2',
            width=1280,
        )
        hint2.add.label(
            'Experimental hint: match every ROOM result to the visible wild-type pFBA reference from the same environment. Compare the reference CYTBD flux with the ROOM significant-change score, not only with mutant biomass.',
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
            title='Mission 33 Hint 1',
            width=1280,
        )
        hint1.add.label(
            'Conceptual hint: a genetic deletion can disable a reaction without forcing a new flux adjustment when that reaction was already unused in the matched reference state.',
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
            title='Mission 33 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Mission 32 identified a cross-branch cut set that disables {MISSION33_TARGET_REACTION}.

            Dr. Chen now asks how much the network must adjust relative to the state that existed before the perturbation.

            ROOM protocol:
            - Objective: {MISSION33_GROWTH_OBJECTIVE}
            - ROOM formulation: integer MILP
            - Delta: {ROOM_DEFAULT_DELTA:g}
            - Epsilon: {ROOM_DEFAULT_EPSILON:g}
            - Linear relaxation: {ROOM_DEFAULT_LINEAR}
            - Every ROOM run uses a wild-type pFBA reference from the same environment
            - The reference is built before gene knockouts are applied

            Matched contexts:
            {context_lines}

            Record these four visible runs in any order:
            {run_lines}

            The ROOM score counts significant flux changes relative to its reference. It is not biomass, total absolute flux or the number of active reactions.

            Compare the reference {MISSION33_TARGET_REACTION} flux with the corresponding ROOM score. Classify the functional state of {MISSION33_TARGET_REACTION} before the knockout in the zero-score reference.
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
            'Mission 33: Reference-State Adjustment Footprint',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Use explicit ROOM references to distinguish a disabled reaction from a reaction that was already unused.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 33 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission33_reference_adjustment_check()
        report_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_options['background_color'] = 'white'
        menu.add.label(
            build_mission33_reference_adjustment_report_text(report),
            **report_options,
        )
        menu.add.vertical_margin(20)

        if '33' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission33 or '33' in self.missions_activated:
            self.mission33 = True
            menu.add.label(
                'Question: Complete with one word: in the zero-score reference, CYTBD was already ______.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'CYTBD was already: ',
                default='',
                input_underline='_',
                maxchar=24,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission33, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission33(self):
        if not is_mission33_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 32 before starting Mission 33.', time=3000)
            return
        if '33' in self.missions_completed:
            return
        if '33' in self.missions_activated:
            self.mission33 = True
            return

        clear_mission33_reference_adjustment_check()
        initialise_mission33_reference_adjustment_screen()
        self.mission33 = True
        self.missions_activated.insert(0, '33')
        animation_text_save('Mission 33 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission33_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 32 first!', time=2500)
            return
        if '33' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 33 before delivering a conclusion.', time=2800)
            return

        report = load_mission33_reference_adjustment_check()
        if (
            not report
            or report.get('mission_id') != '33'
            or report.get('check_version') != MISSION33_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 33 comparison first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('zero_footprint_explained'):
            self.failed.play()
            animation_text_save('Complete all four matched pFBA and ROOM runs first.', time=3000)
            return
        if not mission33_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Enter the one-word functional state of CYTBD in the zero-score reference.', time=3000)
            return

        self.success.play()
        if '33' not in self.missions_completed:
            self.missions_completed.insert(0, '33')
        animation_text_save('Congratulations! Mission 33 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
