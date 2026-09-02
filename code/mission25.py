import pygame
import pygame_menu

from answer_penalty import penalize_wrong_answer

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from mission26 import Mission26_info
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION25_CHECK_VERSION,
    MISSION25_METHOD,
    MISSION25_GROWTH_OBJECTIVE,
    MISSION25_TARGET_GENE,
    MISSION25_TARGET_GENE_NAME,
    MISSION25_OXYGEN_REACTION,
    build_mission25_context_report_text,
    initialise_mission25_context_matrix,
    is_mission25_unlocked,
    mission25_answer_matches,
)


class Mission25:
    """Dr. Smith interaction entry point beginning with Mission 25."""

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
        self.menu25 = Mission25_info(self.toggle_menu, self.player)
        self.menu26 = Mission26_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Smith.",
            "Dr. Luna is still completing your sensitivity training.",
            "Finish Mission 24 before beginning my first experiment.",
        ]
        intro_dialogue = [
            f"Welcome, {self.player.player_name}. I'm Dr. Smith.",
            "A gene effect can change when the surrounding environment changes.",
            "Mission 25 asks you to prove that relationship with a controlled matrix.",
        ]
        active_dialogue = [
            "Mission 25 is active.",
            "Complete every cell of the oxygen-by-genotype matrix.",
            "Return when the visible evidence supports one context-dependent conclusion.",
        ]
        intro26_dialogue = [
            f"Good work, {self.player.player_name}.",
            "Mission 25 showed that the same knockout depends strongly on oxygen context.",
            "Mission 26 extends those endpoints into matched wild-type and knockout curves.",
        ]
        active26_dialogue = [
            "Mission 26 is active.",
            "Record one oxygen Bound Sweep for wild type and one for the b3956 knockout.",
            "Return when the matched curves support a threshold conclusion.",
        ]
        completed26_dialogue = [
            f"Excellent work, {self.player.player_name}.",
            "You distinguished a gradual response from a genotype-specific collapse threshold.",
            "Dr. Ribeiro will continue the campaign in Mission 27.",
        ]

        self.input()
        if '26' in self.missions_completed:
            self.menu_message(completed26_dialogue, buttons=False)
        elif '26' in self.missions_activated:
            self.menu_message(active26_dialogue, menu_to_open=self.menu26)
        elif '25' in self.missions_completed:
            self.menu_message(intro26_dialogue, menu_to_open=self.menu26)
        elif '25' in self.missions_activated:
            self.menu_message(active_dialogue, menu_to_open=self.menu25)
        elif self.player.is_mission_unlocked('25'):
            self.menu_message(intro_dialogue, menu_to_open=self.menu25)
        else:
            self.menu_message(locked_dialogue, buttons=False)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image = get_dialogue_portrait(get_resource_path('graphics/dialogues/smith.jpg'), (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_name, 'Dr. Smith')
        self.screen.blit(name, (47, 677))

        for line, message_line in enumerate(message):
            message_line = prepare_dialogue_text(message_line, self.player.player_name)
            surface = get_dialogue_text_surface(self.font, message_line)
            self.screen.blit(surface, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu25).update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission25_info:
    """Mission 25 — Context-Dependent Gene Essentiality."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)
        self.mission25 = '25' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '25', self.missions_completed, mytheme)

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
            title='Mission 25',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('25'):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 25 is locked. Complete Mission 24 before beginning Dr. Smith's first experiment.",
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
            theme=mytheme, title='Mission 25 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f"Technical hint: use {MISSION25_METHOD} with objective {MISSION25_GROWTH_OBJECTIVE}. Keep every environmental bound at model default for the aerobic cells. For the anaerobic cells, close only the lower bound of {MISSION25_OXYGEN_REACTION}. Use either every gene active or only {MISSION25_TARGET_GENE} / {MISSION25_TARGET_GENE_NAME} knocked out.",
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 25 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: construct four cells—wild type and knockout with oxygen available, then the same two genotypes with oxygen uptake blocked. Compare knockout growth with its own wild-type reference inside each oxygen context.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 25 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: essentiality is conditional. A gene may be dispensable when one route is available but operationally essential when the environment removes an alternative route.',
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
            title='Mission 25 Briefing',
            width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Smith wants a two-by-two controlled matrix for the highlighted gene {MISSION25_TARGET_GENE} / {MISSION25_TARGET_GENE_NAME}.

            Factors:
            - Oxygen context: available or uptake blocked
            - Genotype: wild type or the highlighted single-gene knockout

            Keep the biomass objective, simulation method, carbon-source setup and every unrelated environmental bound equivalent across the matrix. The report records growth, glucose uptake, oxygen uptake and method-aware diagnostics from each visible simulation.

            Compare knockout-to-reference growth retention separately inside the two oxygen contexts. Then submit the context in which the same knockout caused the more severe growth defect.

            Report the result only for this model, objective and medium. Do not interpret it as universal biological essentiality.
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
            'Mission 25: Context-Dependent Gene Essentiality',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            f'Build a controlled oxygen-by-genotype matrix for {MISSION25_TARGET_GENE} / {MISSION25_TARGET_GENE_NAME}.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 25 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission25_comparison_check()
        report_label_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_label_options['background_color'] = 'white'
        menu.add.label(
            build_mission25_context_report_text(report),
            **report_label_options,
        )
        menu.add.vertical_margin(20)

        if '25' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission25 or '25' in self.missions_activated:
            self.mission25 = True
            menu.add.label(
                'Question: In which oxygen context did the same knockout produce the strongest predicted growth defect?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Oxygen context: ',
                default='',
                input_underline='_',
                maxchar=80,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission25, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission25(self):
        if not self.player.is_mission_unlocked('25'):
            self.failed.play()
            animation_text_save('Complete Mission 24 before starting Mission 25.', time=3000)
            return
        if '25' in self.missions_completed:
            return
        if '25' in self.missions_activated:
            self.mission25 = True
            return

        clear_mission25_comparison_check()
        initialise_mission25_context_matrix()
        self.mission25 = True
        self.missions_activated.insert(0, '25')
        animation_text_save('Mission 25 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('25'):
            self.failed.play()
            animation_text_save('Complete Mission 24 first!', time=2500)
            return
        if '25' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 25 before delivering a conclusion.', time=2800)
            return

        report = load_mission25_comparison_check()
        if (
            not report
            or report.get('mission_id') != '25'
            or report.get('check_version') != MISSION25_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 25 matrix first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('Complete all four controlled matrix cells before answering.', time=3000)
            return
        if not mission25_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recompare knockout growth retention inside each oxygen context.', time=3200)
            penalize_wrong_answer(self.player, '25')
            return

        self.success.play()
        if '25' not in self.missions_completed:
            self.missions_completed.insert(0, '25')
        animation_text_save('Congratulations! Mission 25 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
