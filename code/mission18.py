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
    MISSION18_CHECK_VERSION,
    MISSION18_METHOD,
    MISSION18_GROWTH_OBJECTIVE,
    MISSION18_CANDIDATE_EXPORTS,
    MISSION18_EXPORT_NAMES,
    MISSION18_REQUIRED_TRACKED_FLUXES,
    MISSION18_MIN_BINDING_VIABILITY_RATIO,
    MISSION18_BASELINE_LIKE_RATIO,
    build_mission18_binding_export_report_text,
    initialise_mission18_binding_export_screen,
    is_mission18_unlocked,
    mission18_answer_matches,
    normalise_mission18_answer,
)


class Mission18_info:
    """Mission 18 — Binding Export Constraints."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission18 = '18' in self.missions_activated

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
            title='Mission 18',
            width=1280,
        )

        if not is_mission18_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 18 is locked. Complete Mission 17 before beginning the export-constraint screen.',
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
            theme=mytheme, title='Mission 18 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION18_METHOD}, objective {MISSION18_GROWTH_OBJECTIVE}, all genes active, and close only the oxygen lower bound for the baseline. Track ' + ', '.join(MISSION18_REQUIRED_TRACKED_FLUXES) + '. Then close separately the upper bound of ' + ' and '.join(MISSION18_CANDIDATE_EXPORTS) + '.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 18 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: compare an upper-bound closure on an export that is active in the baseline with a closure on an export that is already zero. A binding constraint must change the feasible optimum, not merely appear in the setup.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 18 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: an upper bound restricts positive export. It only becomes binding when the unconstrained baseline needs flux in that direction.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 18 Briefing', width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Rio now wants a causal comparison of export constraints.

            Phase A — anaerobic baseline:
            Use {MISSION18_METHOD}, the biomass objective, all genes active and default glucose. Close only the oxygen lower bound. Select the complete product/byproduct panel and record growth, uptake and export values.

            Phase B — two upper-bound trials:
            Repeat the same setup twice. In each trial, close only one candidate export upper bound and keep every other environmental bound identical to the baseline.

            A binding trial must retain at least {MISSION18_MIN_BINDING_VIABILITY_RATIO * 100:.0f}% of baseline growth while producing a measurable solution response. The non-binding control should retain at least {MISSION18_BASELINE_LIKE_RATIO * 100:.0f}% with a baseline-like export profile.

            The final field asks only for the binding export route. It is not a free-form essay.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidates_text = '   '.join(
            f"{MISSION18_EXPORT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
            for reaction_id in MISSION18_CANDIDATE_EXPORTS
        )
        menu.add.vertical_margin(20)
        menu.add.label('Mission 18: Binding Export Constraints', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            'Record one anaerobic baseline, then close each candidate upper bound separately and determine which constraint actually changes the solution.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Candidate export routes:\n{candidates_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=24,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 18 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission18:
            report = load_mission18_export_bottleneck_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '18'
                or report.get('check_version') != MISSION18_CHECK_VERSION
            ):
                report = initialise_mission18_binding_export_screen()
            menu.add.label(
                build_mission18_binding_export_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.label(
                'Question: Which upper-bound closure created the binding export constraint in this controlled screen?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Binding export route: ',
                default='',
                input_underline='_',
                maxchar=40,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission18, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission18(self):
        if not is_mission18_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 17 before starting Mission 18.', time=3000)
            return
        if '18' in self.missions_completed:
            return
        if '18' in self.missions_activated:
            self.mission18 = True
            return

        clear_mission18_export_bottleneck_check()
        initialise_mission18_binding_export_screen()
        self.mission18 = True
        self.missions_activated.insert(0, '18')
        animation_text_save('Mission 18 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission18_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 17 first!', time=2500)
            return
        if '18' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 18 before delivering a conclusion.', time=2800)
            return

        report = load_mission18_export_bottleneck_check()
        if (
            not report
            or report.get('mission_id') != '18'
            or report.get('check_version') != MISSION18_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the Mission 18 baseline and controlled screen first.', time=3000)
            return
        if not report.get('baseline_ready'):
            self.failed.play()
            animation_text_save('Record the complete anaerobic baseline first.', time=3000)
            return
        if not report.get('screen_complete'):
            self.failed.play()
            animation_text_save('Record both controlled upper-bound trials first.', time=3000)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible comparison does not identify one binding constraint.', time=3000)
            return
        if len(normalise_mission18_answer(answer)) != 1:
            self.failed.play()
            animation_text_save('Enter exactly one candidate export route.', time=2800)
            return
        if not mission18_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That route is not supported by the recorded baseline and trials.', time=3000)
            return

        self.success.play()
        if '18' not in self.missions_completed:
            self.missions_completed.insert(0, '18')
        animation_text_save('Congratulations! Mission 18 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
