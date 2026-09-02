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
from mission30 import Mission30_info
from mission31 import Mission31_info
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION29_CHECK_VERSION,
    MISSION29_METHOD,
    MISSION29_GROWTH_OBJECTIVE,
    MISSION29_PAIR_ORDER,
    MISSION29_PAIRS,
    MISSION29_PAIR_LABELS,
    MISSION29_GENE_NAMES,
    MISSION29_PAIR_REACTIONS,
    MISSION29_SINGLE_GENES,
    build_mission29_redundancy_report_text,
    initialise_mission29_redundancy_screen,
    is_mission29_unlocked,
    mission29_answer_matches,
)


class Mission29:
    """Dr. Li interaction entry point beginning with Mission 29."""

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
        self.menu29 = Mission29_info(self.toggle_menu, self.player)
        self.menu30 = Mission30_info(self.toggle_menu, self.player)
        self.menu31 = Mission31_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Li.",
            "Dr. Ribeiro is still completing your bypass-analysis training.",
            "Finish Mission 28 before entering my network-robustness programme.",
        ]
        intro_dialogue = [
            f"Welcome, {self.player.player_name}. I'm Dr. Li.",
            "Dr. Ribeiro showed you how one function can make a rescue possible.",
            "Now determine how duplicated functions can hide a genetic vulnerability.",
        ]
        active_dialogue = [
            "Mission 29 is active.",
            "Keep the default aerobic medium fixed and compare each matched knockout set.",
            "Infer redundancy from growth retention and the GPR-disabled reactions.",
        ]
        mission30_intro_dialogue = [
            f"Excellent work, {self.player.player_name}.",
            "You found a redundancy pattern in one aerobic environment.",
            "Now test whether that conclusion survives progressive oxygen limitation.",
        ]
        mission30_active_dialogue = [
            "Mission 30 is active.",
            "Build the four matched oxygen curves from the same default base environment.",
            "Keep INFEASIBLE distinct from a measured growth value of zero.",
        ]
        mission31_intro_dialogue = [
            f"Excellent threshold analysis, {self.player.player_name}.",
            "Now reverse the question across matched carbon environments.",
            "Test whether another entry route suppresses the aconitase phenotype.",
        ]
        mission31_active_dialogue = [
            "Mission 31 is active.",
            "Replace glucose with one source and record matched WT and double-KO runs.",
            "Compare growth, uptake and the two disabled aconitase reactions.",
        ]
        mission31_completed_dialogue = [
            f"Excellent work, {self.player.player_name}.",
            "You showed that synthetic lethality depends on the tested environment.",
            "Dr. Chen will continue this laboratory programme.",
        ]

        self.input()
        if '31' in self.missions_completed:
            self.menu_message(mission31_completed_dialogue, buttons=False)
        elif '31' in self.missions_activated:
            self.menu_message(mission31_active_dialogue, menu_to_open=self.menu31)
        elif '30' in self.missions_completed:
            self.menu_message(mission31_intro_dialogue, menu_to_open=self.menu31)
        elif '30' in self.missions_activated:
            self.menu_message(mission30_active_dialogue, menu_to_open=self.menu30)
        elif '29' in self.missions_completed:
            self.menu_message(mission30_intro_dialogue, menu_to_open=self.menu30)
        elif '29' in self.missions_activated:
            self.menu_message(active_dialogue, menu_to_open=self.menu29)
        elif self.player.is_mission_unlocked('29'):
            self.menu_message(intro_dialogue, menu_to_open=self.menu29)
        else:
            self.menu_message(locked_dialogue, buttons=False)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image = get_dialogue_portrait(get_resource_path('graphics/dialogues/li.jpg'), (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_name, 'Dr. Li')
        self.screen.blit(name, (72, 677))

        for line, message_line in enumerate(message):
            message_line = prepare_dialogue_text(message_line, self.player.player_name)
            surface = get_dialogue_text_surface(self.font, message_line)
            self.screen.blit(surface, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu29).update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission29_info:
    """Mission 29 — Isoenzyme Redundancy Screen, Dr. Li."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission29 = '29' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '29', self.missions_completed, mytheme)

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
            title='Mission 29',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('29'):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 29 is locked. Complete Mission 28 before beginning Dr. Li's network-robustness programme.",
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        pair_lines = '\n'.join(
            f"- {MISSION29_PAIR_LABELS[pair_id]}: "
            f"{MISSION29_PAIRS[pair_id][0]} / {MISSION29_GENE_NAMES[MISSION29_PAIRS[pair_id][0]]} + "
            f"{MISSION29_PAIRS[pair_id][1]} / {MISSION29_GENE_NAMES[MISSION29_PAIRS[pair_id][1]]}"
            for pair_id in MISSION29_PAIR_ORDER
        )

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 29 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f"Technical hint: use {MISSION29_METHOD} with objective {MISSION29_GROWTH_OBJECTIVE}. Keep the environmental medium completely default. Record one wild-type reference, every highlighted gene as an individual knockout, and each exact matched two-gene pair. No Production Flux selection is required.",
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 29 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: compare each double knockout with both of its own single knockouts, not only with wild type. A redundant partner can mask the effect of the first deletion until both alternatives are unavailable.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 29 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: synthetic lethality is a non-additive relationship. Look for a pair in which either single knockout retains growth, but removing both matched alternatives abolishes the phenotype.',
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
            title='Mission 29 Briefing',
            width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Li wants a controlled isoenzyme-redundancy screen.

            Fixed protocol:
            - Method: {MISSION29_METHOD}
            - Objective: {MISSION29_GROWTH_OBJECTIVE}
            - Keep the complete environmental medium at model default
            - Use no supplement and no unrelated knockout

            Record one wild-type reference. For every pair below, record both individual knockouts and then the exact matched double knockout:
            {pair_lines}

            The report accumulates ten visible runs in any order. Compare growth retention and the reactions disabled through the complete GPR. Identify the pair whose individual deletions remain tolerated but whose combined deletion abolishes predicted growth.

            This is an operational interaction in this model, objective, medium and tested pair set; it is not a universal claim about the genes.
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
            'Mission 29: Isoenzyme Redundancy Screen',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Distinguish ordinary pathway redundancy from a non-additive double-knockout interaction.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 29 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission29_redundancy_check()
        report_label_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_label_options['background_color'] = 'white'
        menu.add.label(
            build_mission29_redundancy_report_text(report),
            **report_label_options,
        )
        menu.add.vertical_margin(20)

        if '29' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission29 or '29' in self.missions_activated:
            self.mission29 = True
            menu.add.label(
                'Question: Which tested gene pair shows a synthetic-lethal interaction under the default aerobic model context?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Gene pair: ',
                default='',
                input_underline='_',
                maxchar=120,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission29, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission29(self):
        if not self.player.is_mission_unlocked('29'):
            self.failed.play()
            animation_text_save('Complete Mission 28 before starting Mission 29.', time=3000)
            return
        if '29' in self.missions_completed:
            return
        if '29' in self.missions_activated:
            self.mission29 = True
            return

        clear_bound_sweep()
        clear_mission29_redundancy_check()
        initialise_mission29_redundancy_screen()
        self.mission29 = True
        self.missions_activated.insert(0, '29')
        animation_text_save('Mission 29 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('29'):
            self.failed.play()
            animation_text_save('Complete Mission 28 first!', time=2500)
            return
        if '29' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 29 before delivering a conclusion.', time=2800)
            return

        report = load_mission29_redundancy_check()
        if (
            not report
            or report.get('mission_id') != '29'
            or report.get('check_version') != MISSION29_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 29 redundancy screen first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('unique_synthetic_lethality_supported'):
            self.failed.play()
            animation_text_save('Complete the wild-type, six single-knockout and three matched double-knockout runs before answering.', time=3600)
            return
        if not mission29_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recompare both single knockouts, the matched double knockout and the GPR-disabled reactions.', time=3400)
            penalize_wrong_answer(self.player, '29')
            return

        self.success.play()
        if '29' not in self.missions_completed:
            self.missions_completed.insert(0, '29')
        animation_text_save('Congratulations! Mission 29 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
