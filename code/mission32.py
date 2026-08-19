import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from mission33 import Mission33_info
from mission34 import Mission34_info
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION32_BRANCH_GENES,
    MISSION32_CHECK_VERSION,
    MISSION32_CONDITION_GENES,
    MISSION32_CONDITION_LABELS,
    MISSION32_CONDITION_ORDER,
    MISSION32_GENE_NAMES,
    MISSION32_GROWTH_OBJECTIVE,
    MISSION32_METHOD,
    MISSION32_TARGET_REACTION,
    build_mission32_respiratory_cut_set_report_text,
    initialise_mission32_respiratory_cut_set_screen,
    is_mission32_unlocked,
    mission32_answer_matches,
)


class Mission32:
    """Dr. Chen interaction entry point beginning with Mission 32."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.screen = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.font_name = pygame.font.Font(font_path, 24)
        self.timer = Timer(200)
        self.menu32 = Mission32_info(self.toggle_menu, self.player)
        self.menu33 = Mission33_info(self.toggle_menu, self.player)
        self.menu34 = Mission34_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked_dialogue = [
            f"Hello, {self.player.player_name}. I'm Dr. Chen.",
            'Dr. Li is still completing your network training.',
            'Finish Mission 31 before starting my GPR programme.',
        ]
        intro_dialogue = [
            f'Welcome, {self.player.player_name}.',
            'Simple redundancy can hide inside a more complex GPR.',
            'Test which knockouts break one branch or the whole reaction.',
        ]
        active_dialogue = [
            'Mission 32 is active.',
            'Keep the aerobic default medium fixed.',
            'Compare branch status, oxygen uptake and the full CYTBD GPR.',
        ]
        mission33_intro_dialogue = [
            f'Excellent work, {self.player.player_name}.',
            'You separated a broken branch from a disabled reaction.',
            'Now measure its adjustment footprint from two references.',
        ]
        mission33_active_dialogue = [
            'Mission 33 is active.',
            'Build matched wild-type pFBA references for both contexts.',
            'Then compare each reference with its ROOM cut-set mutant.',
        ]
        mission34_intro_dialogue = [
            f'Excellent reference analysis, {self.player.player_name}.',
            'You separated genetic loss from reference-state use.',
            'Now test whether one shared knockout can match two separate knockouts.',
        ]
        mission34_active_dialogue = [
            'Mission 34 is active.',
            'Keep the default aerobic pFBA protocol fixed.',
            'Compare disabled-reaction sets before comparing gene counts.',
        ]
        mission34_completed_dialogue = [
            f'Excellent work, {self.player.player_name}.',
            'You mapped different genotypes to the same reaction-level lesion.',
            'My programme is complete. Prepare for the E. coli finale.',
        ]

        self.input()
        if '34' in self.missions_completed:
            self.menu_message(mission34_completed_dialogue, buttons=False)
        elif '34' in self.missions_activated:
            self.menu_message(mission34_active_dialogue, menu_to_open=self.menu34)
        elif '33' in self.missions_completed:
            self.menu_message(mission34_intro_dialogue, menu_to_open=self.menu34)
        elif '33' in self.missions_activated:
            self.menu_message(mission33_active_dialogue, menu_to_open=self.menu33)
        elif '32' in self.missions_completed:
            self.menu_message(mission33_intro_dialogue, menu_to_open=self.menu33)
        elif '32' in self.missions_activated:
            self.menu_message(active_dialogue, menu_to_open=self.menu32)
        elif is_mission32_unlocked(self.missions_completed):
            self.menu_message(intro_dialogue, menu_to_open=self.menu32)
        else:
            self.menu_message(locked_dialogue, buttons=False)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image = get_dialogue_portrait(get_resource_path('graphics/dialogues/chen.jpg'), (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_name, 'Dr. Chen')
        self.screen.blit(name, (60, 677))

        for line, message_line in enumerate(message):
            message_line = prepare_dialogue_text(message_line, self.player.player_name)
            surface = get_dialogue_text_surface(self.font, message_line)
            self.screen.blit(surface, (200, 525 + (line * 35)))

        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu32).update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission32_info:
    """Mission 32 — Respiratory Complex Cut-Set, Dr. Chen."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission32 = '32' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '32', self.missions_completed, mytheme)

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
            title='Mission 32',
            width=1280,
        )

        if not is_mission32_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 32 is locked. Complete Mission 31 before beginning Dr. Chen's GPR-architecture programme.",
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        condition_lines = '\n'.join(
            f'- {MISSION32_CONDITION_LABELS[condition_id]}'
            for condition_id in MISSION32_CONDITION_ORDER
        )

        hint3 = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 32 Hint 3',
            width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION32_METHOD} with objective {MISSION32_GROWTH_OBJECTIVE}. Keep every environmental bound at model default. Record exactly the six highlighted genotypes. No Production Flux selection is required; use the visible Exchange Flux Report and the GPR-disabled reactions.',
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
            title='Mission 32 Hint 2',
            width=1280,
        )
        hint2.add.label(
            'Experimental hint: compare the two branch states with measured oxygen uptake. A branch can be broken while the complete reaction remains available through the alternative branch.',
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
            title='Mission 32 Hint 1',
            width=1280,
        )
        hint1.add.label(
            'Conceptual hint: each respiratory branch uses AND logic between its subunits, while the two complete branches are linked by OR. The full GPR fails only when both alternatives are broken.',
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
            title='Mission 32 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Chen now moves from simple isoenzyme redundancy to a nested gene-protein-reaction rule.

            Target reaction:
            - {MISSION32_TARGET_REACTION}
            - GPR: (b0978 AND b0979) OR (b0733 AND b0734)
            - cbdAB branch: {MISSION32_BRANCH_GENES['cbdAB'][0]} / {MISSION32_GENE_NAMES[MISSION32_BRANCH_GENES['cbdAB'][0]]} + {MISSION32_BRANCH_GENES['cbdAB'][1]} / {MISSION32_GENE_NAMES[MISSION32_BRANCH_GENES['cbdAB'][1]]}
            - cydAB branch: {MISSION32_BRANCH_GENES['cydAB'][0]} / {MISSION32_GENE_NAMES[MISSION32_BRANCH_GENES['cydAB'][0]]} + {MISSION32_BRANCH_GENES['cydAB'][1]} / {MISSION32_GENE_NAMES[MISSION32_BRANCH_GENES['cydAB'][1]]}

            Fixed protocol:
            - Method: {MISSION32_METHOD}
            - Objective: {MISSION32_GROWTH_OBJECTIVE}
            - Completely model-default aerobic environment
            - No Production Flux selection is required

            Record these six visible conditions in any order:
            {condition_lines}

            Compare growth, measured oxygen uptake, both branch states and the complete GPR result. The target pair must remain a feasible reduced-growth solution rather than an INFEASIBLE state.

            Identify which tested pair breaks one required subunit in each alternative branch and therefore disables {MISSION32_TARGET_REACTION}.
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
            'Mission 32: Respiratory Complex Cut-Set',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Resolve nested AND/OR GPR logic and identify the tested pair that disables the complete respiratory reaction.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 32 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission32_respiratory_cut_set_check()
        report_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_options['background_color'] = 'white'
        menu.add.label(
            build_mission32_respiratory_cut_set_report_text(report),
            **report_options,
        )
        menu.add.vertical_margin(20)

        if '32' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission32 or '32' in self.missions_activated:
            self.mission32 = True
            menu.add.label(
                'Question: Which tested knockout pair broke one required subunit in each alternative CYTBD branch and disabled the reaction?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Knockout pair: ',
                default='',
                input_underline='_',
                maxchar=120,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission32, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission32(self):
        if not is_mission32_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 31 before starting Mission 32.', time=3000)
            return
        if '32' in self.missions_completed:
            return
        if '32' in self.missions_activated:
            self.mission32 = True
            return

        clear_mission32_respiratory_cut_set_check()
        initialise_mission32_respiratory_cut_set_screen()
        self.mission32 = True
        self.missions_activated.insert(0, '32')
        animation_text_save('Mission 32 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission32_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 31 first!', time=2500)
            return
        if '32' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 32 before delivering a conclusion.', time=2800)
            return

        report = load_mission32_respiratory_cut_set_check()
        if (
            not report
            or report.get('mission_id') != '32'
            or report.get('check_version') != MISSION32_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 32 screen first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('unique_cut_set_supported'):
            self.failed.play()
            animation_text_save('Complete all six controlled runs before answering.', time=3000)
            return
        if not mission32_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Compare the two branch states and the complete CYTBD GPR.', time=3000)
            return

        self.success.play()
        if '32' not in self.missions_completed:
            self.missions_completed.insert(0, '32')
        animation_text_save('Congratulations! Mission 32 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
