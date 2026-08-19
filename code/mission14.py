import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from async_menu import run_menu
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION14_CHECK_VERSION,
    MISSION14_TARGET_METHOD,
    MISSION14_TARGET_OBJECTIVE,
    MISSION14_TARGET_PRODUCT,
    MISSION14_COPRODUCT_PRODUCT,
    MISSION14_CANDIDATE_GENES,
    MISSION14_GENE_NAMES,
    MISSION14_REQUIRED_TRACKED_FLUXES,
    MISSION14_PRODUCT_NAMES,
    MISSION14_MIN_TARGET_RETENTION,
    MISSION14_MIN_ACETATE_REDUCTION,
    MISSION14_NEW_BYPRODUCT_THRESHOLD,
    build_mission14_tradeoff_report_text,
    initialise_mission14_tradeoff_screening,
    is_mission14_unlocked,
    mission14_answer_matches,
    normalise_mission14_answer,
)


class Mission14_info:
    """Mission 14 — Byproduct Trade-off Screening.

    The player screens four single-gene interventions under the same visible
    pFBA succinate-optimal setup and evaluates the complete co-product profile.
    A negative conclusion is valid when no candidate is a clean improvement.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission14 = '14' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '14', self.missions_completed, mytheme)

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
            title='Mission 14',
            width=1280,
        )

        if not is_mission14_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 14 is locked. Complete Mission 13 before screening genetic trade-offs.',
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
            theme=mytheme, title='Mission 14 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION14_TARGET_METHOD} with objective {MISSION14_TARGET_OBJECTIVE}; keep default glucose, close only the lower bound of EX_o2_e, and track ' + ', '.join(MISSION14_REQUIRED_TRACKED_FLUXES) + '. Test exactly one of the four candidate genes per run. The Mission 13 pFBA run can supply the no-knockout reference.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 14 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: keep method, objective, medium and exchange panel identical. Compare each candidate with the no-knockout reference using target retention, acetate reduction and any newly positive co-products.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 14 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: a lower value for one byproduct is not automatically an improvement. Carbon may move into a different secreted product, and the primary target can decrease.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 14 Briefing', width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Almeida now wants an intervention screen rather than a single favourable number. Keep the anaerobic {MISSION14_TARGET_METHOD} problem from Mission 13 and test every highlighted single-gene knockout.

            The reference predicts {MISSION14_COPRODUCT_PRODUCT} alongside {MISSION14_TARGET_PRODUCT}. For each candidate, inspect the full visible exchange fingerprint. A clean improvement must retain enough target flux, reduce acetate meaningfully and avoid creating another positive co-product.

            A negative screening result is scientifically valid. Do not force a winner: base the final conclusion strictly on the complete evidence.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidate_text = '   '.join(
            f"{gene_id} ({MISSION14_GENE_NAMES.get(gene_id, '')})"
            for gene_id in MISSION14_CANDIDATE_GENES
        )
        panel_text = '   '.join(
            f"{MISSION14_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
            for reaction_id in MISSION14_REQUIRED_TRACKED_FLUXES
        )

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 14: Byproduct Trade-off Screening',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Screen every candidate and decide whether any single knockout improves the complete succinate/co-product profile cleanly.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Candidate genes:\n{candidate_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=25,
            padding=(5, 0, 0, 35),
        )
        menu.add.label(
            f'Complete target/co-product panel:\n{panel_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=25,
            padding=(5, 0, 0, 35),
        )
        menu.add.label(
            f'Clean-improvement criteria: retain at least {MISSION14_MIN_TARGET_RETENTION * 100:.0f}% of reference succinate; reduce acetate by at least {MISSION14_MIN_ACETATE_REDUCTION:.1f}; no new co-product above {MISSION14_NEW_BYPRODUCT_THRESHOLD:.1f}.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=23,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 14 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission14:
            report = load_mission14_reduction_check()
            menu.add.label(
                build_mission14_tradeoff_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'Screening conclusion: ',
                default='',
                input_underline='_',
                maxchar=60,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission14, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission14(self):
        if not is_mission14_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 13 before starting Mission 14.', time=3000)
            return
        if '14' in self.missions_completed:
            self.mission14 = True
            animation_text_save('Mission 14 is already completed.', time=2500)
            return
        if '14' in self.missions_activated:
            self.mission14 = True
            animation_text_save('Mission 14 is already active.', time=2500)
            return

        clear_mission14_reduction_check()
        initialise_mission14_tradeoff_screening()
        self.mission14 = True
        if '14' not in self.missions_activated:
            self.missions_activated.insert(0, '14')
        animation_text_save('Mission 14 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission14_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 13 first!', time=2500)
            return
        if '14' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 14 before delivering results.', time=3000)
            return

        report = load_mission14_reduction_check()
        if (
            not report
            or report.get('mission_id') != '14'
            or report.get('check_version') != MISSION14_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Build the controlled Mission 14 candidate screen first.', time=3000)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            animation_text_save('Record the complete reference and all four visible candidate trials before answering.', time=3400)
            return
        if normalise_mission14_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter the conclusion supported by the completed candidate screen.', time=3400)
            return
        if not mission14_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That conclusion does not match the complete target-retention and co-product evidence.', time=3400)
            return

        self.success.play()
        if '14' not in self.missions_completed:
            self.missions_completed.insert(0, '14')
        animation_text_save('Congratulations! Mission 14 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
