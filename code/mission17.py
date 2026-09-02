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
    MISSION17_CHECK_VERSION,
    MISSION17_METHOD,
    MISSION17_GROWTH_OBJECTIVE,
    MISSION17_CANDIDATE_NUTRIENTS,
    MISSION17_NUTRIENT_NAMES,
    MISSION17_COLLAPSE_RATIO,
    MISSION17_PRESERVED_RATIO,
    build_mission17_essential_routes_report_text,
    initialise_mission17_essential_routes,
    is_mission17_unlocked,
    mission17_answer_matches,
    normalise_mission17_answer,
)


class Mission17_info:
    """Mission 17 — Essential Uptake Routes."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission17 = '17' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '17', self.missions_completed, mytheme)

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
            title='Mission 17',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('17'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 17 is locked. Complete Mission 16 before beginning the uptake-route screen.',
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
            theme=mytheme, title='Mission 17 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f'Technical hint: first use {MISSION17_METHOD}, objective {MISSION17_GROWTH_OBJECTIVE}, all genes active and every environmental bound at default. Then repeat the same setup five times, closing only one candidate lower bound per run: ' + ', '.join(MISSION17_CANDIDATE_NUTRIENTS) + '.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 17 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: compare every trial with the same recorded baseline. A lower-bound closure removes uptake capacity; it does not necessarily remove positive secretion through that exchange.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 17 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: use the sign of each baseline exchange flux. Negative flux indicates uptake; positive flux indicates secretion under the displayed solution.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 17 Briefing', width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Rio now wants to distinguish uptake routes that are required for growth from exchanges that are operating mainly in the secretion direction.

            Phase A — controlled baseline:
            Use {MISSION17_METHOD}, the biomass objective, all genes active and the complete model-default environment. Record the signed exchange fluxes in the Exchange Flux Report.

            Phase B — lower-bound screen:
            Repeat the same experiment five times. In each run, close only the lower bound of one candidate exchange and keep every other environmental bound at default. Compare predicted growth with the recorded baseline.

            A trial at or below {MISSION17_COLLAPSE_RATIO * 100:.1f}% of baseline is treated as growth collapse. A trial at or above {MISSION17_PRESERVED_RATIO * 100:.1f}% retains baseline-like growth.

            The final field asks only for the two route names or reaction identifiers. It is not a free-form essay.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidates_text = '   '.join(
            f"{MISSION17_NUTRIENT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
            for reaction_id in MISSION17_CANDIDATE_NUTRIENTS
        )
        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 17: Essential Uptake Routes',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Record one default-medium baseline, then close each candidate lower bound separately and compare the five growth responses.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Candidate exchanges:\n{candidates_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=24,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 17 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission17:
            report = load_mission17_essential_medium_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '17'
                or report.get('check_version') != MISSION17_CHECK_VERSION
            ):
                report = initialise_mission17_essential_routes()
            menu.add.label(
                build_mission17_essential_routes_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.label(
                'Question: Which two candidate uptake routes caused growth to collapse when their lower bounds were closed?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Required uptake routes: ',
                default='',
                input_underline='_',
                maxchar=60,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission17, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission17(self):
        if not self.player.is_mission_unlocked('17'):
            self.failed.play()
            animation_text_save('Complete Mission 16 before starting Mission 17.', time=3000)
            return
        if '17' in self.missions_completed:
            return
        if '17' in self.missions_activated:
            self.mission17 = True
            return

        clear_mission17_essential_medium_check()
        initialise_mission17_essential_routes()
        self.mission17 = True
        self.missions_activated.insert(0, '17')
        animation_text_save('Mission 17 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('17'):
            self.failed.play()
            animation_text_save('Complete Mission 16 first!', time=2500)
            return
        if '17' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 17 before delivering a conclusion.', time=2800)
            return

        report = load_mission17_essential_medium_check()
        if (
            not report
            or report.get('mission_id') != '17'
            or report.get('check_version') != MISSION17_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the Mission 17 baseline and controlled screen first.', time=3000)
            return
        if not report.get('baseline_ready'):
            self.failed.play()
            animation_text_save('Record the complete default-medium baseline first.', time=3000)
            return
        if not report.get('screen_complete'):
            self.failed.play()
            animation_text_save('Record all five controlled lower-bound trials first.', time=3200)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible screen does not show the expected two-collapse pattern.', time=3200)
            return
        if len(normalise_mission17_answer(answer)) != 2:
            self.failed.play()
            animation_text_save('Enter exactly two candidate route names or reaction identifiers.', time=3000)
            penalize_wrong_answer(self.player, '17')
            return
        if not mission17_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Those two routes are not supported by the recorded growth responses.', time=3000)
            penalize_wrong_answer(self.player, '17')
            return

        self.success.play()
        if '17' not in self.missions_completed:
            self.missions_completed.insert(0, '17')
        animation_text_save('Congratulations! Mission 17 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()
