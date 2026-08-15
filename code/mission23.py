import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from mission24 import Mission24_info
from utils import *
from simulation import (
    MISSION23_CHECK_VERSION,
    MISSION23_METHOD,
    MISSION23_GROWTH_OBJECTIVE,
    MISSION23_SWEEP_REACTION,
    MISSION23_SWEEP_VALUES,
    MISSION23_REQUIRED_TRACKED_FLUXES,
    MISSION23_REQUIRED_MEDIUM_FLUXES,
    build_mission23_nutrient_sensitivity_report_text,
    initialise_mission23_nutrient_sensitivity_curve,
    is_mission23_unlocked,
    mission23_answer_matches,
    normalise_mission23_answer,
)


class Mission23:
    """Dr. Luna's two-mission sensitivity sequence (Missions 23 and 24)."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu

        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.font_nome = pygame.font.Font(font_path, 24)
        self.screen = pygame.display.get_surface()
        self.timer = Timer(200)

        self.menu23 = Mission23_info(self.toggle_menu, self.player)
        self.menu24 = Mission24_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked_dialogue = [
            "Dr. Vega is still completing your controlled-comparison training.",
            "Complete Mission 22 before beginning Dr. Luna's sensitivity laboratory.",
        ]

        intro23_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Luna.",
            "Dr. Vega compared isolated endpoints. I study what happens between them.",
            "Begin with a nutrient-sensitivity curve across controlled ammonium levels.",
        ]
        active23_dialogue = [
            "Mission 23 is active. Configure the ammonium Bound Sweep.",
            "Keep the base model unchanged and inspect every response row.",
            "Submit the secretion supported by the onset of nutrient limitation.",
        ]
        intro24_dialogue = [
            f"Good work, {self.player.player_name}.",
            "You found the onset of a response under graded nutrient limitation.",
            "Now restrict an export route gradually and read the order of changes.",
        ]
        active24_dialogue = [
            "Mission 24 is active. Configure the CO2 upper-bound sweep.",
            "Find the non-binding cap, then the first binding cap.",
            "Submit the first compensatory secretion supported by the curve.",
        ]
        completed24_dialogue = [
            f"Excellent analysis, {self.player.player_name}.",
            "You completed Dr. Luna's sensitivity laboratory.",
            "Dr. Smith will continue the campaign in Mission 25.",
        ]

        self.input()
        if not is_mission23_unlocked(self.missions_completed):
            self.menu_message(locked_dialogue, buttons=False)
        elif '24' in self.missions_completed:
            self.menu_message(completed24_dialogue, buttons=False)
        elif '24' in self.missions_activated:
            self.menu_message(active24_dialogue, menu_to_open=self.menu24)
        elif '23' in self.missions_completed:
            self.menu_message(intro24_dialogue, menu_to_open=self.menu24)
        elif '23' in self.missions_activated:
            self.menu_message(active23_dialogue, menu_to_open=self.menu23)
        else:
            self.menu_message(intro23_dialogue, menu_to_open=self.menu23)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image_path = get_resource_path('graphics/dialogues/luna.jpg')
        image = pygame.image.load(image_path).convert()
        if image.get_size() != (150, 150):
            image = pygame.transform.smoothscale(image, (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = self.font_nome.render('Dr. Luna', True, 'black')
        self.screen.blit(name, (52, 677))

        for line, message_line in enumerate(message):
            message_line = prepare_dialogue_text(message_line, self.player.player_name)
            surface = self.font.render(message_line, True, 'black')
            self.screen.blit(surface, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                target_menu = menu_to_open or self.menu23
                self.pending = target_menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission23_info:
    """Mission 23 — Nutrient Sensitivity Curve."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission23 = '23' in self.missions_activated

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
            title='Mission 23',
            width=1280,
        )

        if not is_mission23_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 23 is locked. Complete Mission 22 before beginning Dr. Luna's sensitivity laboratory.",
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
            theme=mytheme, title='Mission 23 Hint 3', width=1280,
        )
        hint3.add.label(
            f"Technical hint: use {MISSION23_METHOD}, objective {MISSION23_GROWTH_OBJECTIVE}, every gene active and a completely default base environment. In Bound Sweep Setup select {MISSION23_SWEEP_REACTION} lower bound and values -5, -4, -2, -1. In Production Flux select " + ', '.join(MISSION23_REQUIRED_TRACKED_FLUXES) + '.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 23 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: the first sweep point is deliberately less restrictive than the realised wild-type ammonium uptake. Find the first tighter point where growth falls, then compare which tracked secretion changed from absent to active.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 23 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: a lower bound defines uptake capacity, not necessarily the flux the optimum will use. A response curve helps distinguish a non-binding point from the onset of nutrient limitation.',
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
            title='Mission 23 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Luna studies graded responses rather than only two endpoints.

            Configure one four-point Bound Sweep:
            - Method: {MISSION23_METHOD}
            - Objective: {MISSION23_GROWTH_OBJECTIVE}
            - Genes: all active
            - Base environment: every lower and upper bound at model default
            - Sweep variable: {MISSION23_SWEEP_REACTION} lower bound
            - Sweep values: {', '.join(f'{value:g}' for value in MISSION23_SWEEP_VALUES)}
            - Production Flux: {', '.join(MISSION23_REQUIRED_TRACKED_FLUXES)}

            The sweep report also records {', '.join(MISSION23_REQUIRED_MEDIUM_FLUXES)} and the pFBA diagnostics for every row.

            Identify the tracked secretion that is absent at the non-limiting point but becomes active at the first ammonium-limited point. Submit one concise route, not an essay.
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
            'Mission 23: Nutrient Sensitivity Curve',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Build one ammonium response curve and determine which tracked secretion emerges at the onset of limitation.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 23 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission23_comparison_check()
        report_label_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        # Before activation there is no experimental report yet.  Keep the
        # introductory status as plain text instead of drawing an empty report
        # card.  Once a real Mission 23 report exists, retain the white panel
        # used to separate the sweep evidence from the rest of the menu.
        if report:
            report_label_options['background_color'] = 'white'

        menu.add.label(
            build_mission23_nutrient_sensitivity_report_text(report),
            **report_label_options,
        )
        menu.add.vertical_margin(20)

        if '23' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission23 or '23' in self.missions_activated:
            self.mission23 = True
            menu.add.label(
                'Question: Which tracked secretion was absent at the non-limiting point but became active when ammonium first became limiting?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'New secretion: ',
                default='',
                input_underline='_',
                maxchar=80,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission23, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission23(self):
        if not is_mission23_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 22 before starting Mission 23.', time=3000)
            return
        if '23' in self.missions_completed:
            return
        if '23' in self.missions_activated:
            self.mission23 = True
            return

        clear_compare_runs()
        clear_bound_sweep()
        clear_mission23_comparison_check()
        initialise_mission23_nutrient_sensitivity_curve()
        self.mission23 = True
        self.missions_activated.insert(0, '23')
        animation_text_save('Mission 23 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission23_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 22 first!', time=2500)
            return
        if '23' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 23 before delivering a conclusion.', time=2800)
            return

        report = load_mission23_comparison_check()
        if (
            not report
            or report.get('mission_id') != '23'
            or report.get('check_version') != MISSION23_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 23 Bound Sweep first.', time=3000)
            return
        if not report.get('all_points_recorded'):
            self.failed.play()
            animation_text_save('Record all four required ammonium sweep points.', time=3000)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible sweep does not yet support the required sensitivity interpretation.', time=3000)
            return
        if normalise_mission23_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter one unambiguous tracked secretion only.', time=2800)
            return
        if not mission23_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That secretion is not supported by the recorded onset of limitation.', time=3000)
            return

        self.success.play()
        if '23' not in self.missions_completed:
            self.missions_completed.insert(0, '23')
        animation_text_save('Congratulations! Mission 23 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
