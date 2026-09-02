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
from mission28 import Mission28_info
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION27_CHECK_VERSION,
    MISSION27_METHOD,
    MISSION27_GROWTH_OBJECTIVE,
    MISSION27_TARGET_GENE,
    MISSION27_TARGET_GENE_NAME,
    MISSION27_TARGET_REACTION,
    MISSION27_CANDIDATE_SUPPLEMENTS,
    MISSION27_CANDIDATE_NAMES,
    build_mission27_rescue_report_text,
    initialise_mission27_rescue_screen,
    is_mission27_unlocked,
    mission27_answer_matches,
)


class Mission27:
    """Dr. Ribeiro interaction entry point beginning with Mission 27."""

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
        self.menu27 = Mission27_info(self.toggle_menu, self.player)
        self.menu28 = Mission28_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Ribeiro.",
            "Dr. Smith is still completing your genotype-environment training.",
            "Finish Mission 26 before entering my laboratory programme.",
        ]
        intro_dialogue = [
            f"Welcome, {self.player.player_name}. I'm Dr. Ribeiro.",
            "You proved that gene effects depend on the environment.",
            "Now reverse the question: can an environmental intervention rescue a genetic failure?",
        ]
        active_dialogue = [
            "Mission 27 is active.",
            "Keep the gltA knockout fixed and change one candidate supplement at a time.",
            "A rescue must restore growth while citrate synthase remains disabled.",
        ]
        mission28_intro_dialogue = [
            f"Excellent work, {self.player.player_name}.",
            "You restored growth while citrate synthase remained disabled.",
            "Now identify the network function that makes that rescue possible.",
        ]
        mission28_active_dialogue = [
            "Mission 28 is active.",
            "Keep the gltA lesion and 2-oxoglutarate rescue medium fixed.",
            "Change one secondary gene at a time; compare growth and supplement uptake.",
        ]
        completed_dialogue = [
            f"Excellent work, {self.player.player_name}.",
            "You moved from detecting a rescue to explaining its model-predicted dependency.",
            "Dr. Li will continue the laboratory programme.",
        ]

        self.input()
        if '28' in self.missions_completed:
            self.menu_message(completed_dialogue, buttons=False)
        elif '28' in self.missions_activated:
            self.menu_message(mission28_active_dialogue, menu_to_open=self.menu28)
        elif '27' in self.missions_completed:
            self.menu_message(mission28_intro_dialogue, menu_to_open=self.menu28)
        elif '27' in self.missions_activated:
            self.menu_message(active_dialogue, menu_to_open=self.menu27)
        elif self.player.is_mission_unlocked('27'):
            self.menu_message(intro_dialogue, menu_to_open=self.menu27)
        else:
            self.menu_message(locked_dialogue, buttons=False)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image = get_dialogue_portrait(get_resource_path('graphics/dialogues/ribeiro.jpg'), (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_name, 'Dr. Ribeiro')
        self.screen.blit(name, (38, 677))

        for line, message_line in enumerate(message):
            message_line = prepare_dialogue_text(message_line, self.player.player_name)
            surface = get_dialogue_text_surface(self.font, message_line)
            self.screen.blit(surface, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu27).update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission27_info:
    """Mission 27 — Metabolic Bypass Rescue."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission27 = '27' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '27', self.missions_completed, mytheme)

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
            title='Mission 27',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('27'):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 27 is locked. Complete Mission 26 before beginning Dr. Ribeiro's first experiment.",
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        candidate_lines = '\n'.join(
            f'- {reaction_id}: {MISSION27_CANDIDATE_NAMES[reaction_id]}'
            for reaction_id in MISSION27_CANDIDATE_SUPPLEMENTS
        )

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 27 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f"Technical hint: use {MISSION27_METHOD} with objective {MISSION27_GROWTH_OBJECTIVE}. Record a completely default wild-type reference, then a completely default single {MISSION27_TARGET_GENE} / {MISSION27_TARGET_GENE_NAME} knockout reference. For every candidate trial keep only that knockout and open exactly one candidate lower bound; leave glucose, oxygen and every unrelated bound at model default. No Production Flux selection is required.",
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 27 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: references and candidate trials can be recorded in any order. A candidate counts only when it is the sole manual medium change and the gltA knockout still disables citrate synthase through its GPR.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 27 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: environmental rescue does not repair a deleted gene. Look for a supplement that restores positive predicted growth while the knockout-defined reaction remains unavailable.',
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
            title='Mission 27 Briefing',
            width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Ribeiro wants a controlled metabolic-rescue screen.

            Genetic lesion:
            - Knock out only {MISSION27_TARGET_GENE} / {MISSION27_TARGET_GENE_NAME}
            - Its GPR disables {MISSION27_TARGET_REACTION} / citrate synthase

            Method and objective:
            - {MISSION27_METHOD}
            - {MISSION27_GROWTH_OBJECTIVE}

            First record two references with the completely default medium:
            - Wild type
            - Single-gene knockout

            Then keep the knockout fixed and test each candidate separately. Open exactly one candidate lower bound per run; do not close glucose or oxygen and do not change any unrelated bound.

            Candidate exchanges:
            {candidate_lines}

            The report accumulates seven visible runs. Identify the candidate that restores positive predicted growth while {MISSION27_TARGET_REACTION} remains disabled. The result is conditional on this model, objective, medium, bounds and candidate set.
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
            'Mission 27: Metabolic Bypass Rescue',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            f'Test whether one environmental supplement can bypass the {MISSION27_TARGET_GENE} / {MISSION27_TARGET_GENE_NAME} lesion without restoring citrate synthase.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 27 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission27_rescue_check()
        report_label_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_label_options['background_color'] = 'white'
        menu.add.label(
            build_mission27_rescue_report_text(report),
            **report_label_options,
        )
        menu.add.vertical_margin(20)

        if '27' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission27 or '27' in self.missions_activated:
            self.mission27 = True
            menu.add.label(
                'Question: Which candidate exchange restored predicted growth while citrate synthase remained disabled?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Rescue candidate: ',
                default='',
                input_underline='_',
                maxchar=100,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission27, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission27(self):
        if not self.player.is_mission_unlocked('27'):
            self.failed.play()
            animation_text_save('Complete Mission 26 before starting Mission 27.', time=3000)
            return
        if '27' in self.missions_completed:
            return
        if '27' in self.missions_activated:
            self.mission27 = True
            return

        clear_bound_sweep()
        clear_mission27_bound_sweep_check()
        clear_mission27_rescue_check()
        initialise_mission27_rescue_screen()
        self.mission27 = True
        self.missions_activated.insert(0, '27')
        animation_text_save('Mission 27 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('27'):
            self.failed.play()
            animation_text_save('Complete Mission 26 first!', time=2500)
            return
        if '27' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 27 before delivering a conclusion.', time=2800)
            return

        report = load_mission27_rescue_check()
        if (
            not report
            or report.get('mission_id') != '27'
            or report.get('check_version') != MISSION27_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 27 rescue screen first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('unique_rescue_supported'):
            self.failed.play()
            animation_text_save('Complete both references and all five controlled candidate trials before answering.', time=3300)
            return
        if not mission27_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recompare candidate growth while confirming that citrate synthase remains disabled.', time=3300)
            penalize_wrong_answer(self.player, '27')
            return

        self.success.play()
        if '27' not in self.missions_completed:
            self.missions_completed.insert(0, '27')
        animation_text_save('Congratulations! Mission 27 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
