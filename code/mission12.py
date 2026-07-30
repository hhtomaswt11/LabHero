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
    MISSION12_CHECK_VERSION,
    MISSION12_COMPETING_FLUXES,
    MISSION12_EXPECTED_NEW_BYPRODUCT,
    MISSION12_GLUCOSE_REACTION,
    MISSION12_METHOD,
    MISSION12_OXYGEN_REACTION,
    MISSION12_PRODUCT_NAMES,
    MISSION12_REQUIRED_TRACKED_FLUXES,
    MISSION12_TARGET_OBJECTIVE,
    MISSION12_TARGET_PRODUCT,
    build_mission12_comparison_report_text,
    is_mission12_unlocked,
    mission12_answer_matches,
    normalise_mission12_answer,
)


class Mission12_info:
    """Mission 12 — Constraint-Driven Succinate Byproducts.

    The player compares two complete, visible succinate-optimal fingerprints.
    Method, objective, genes, glucose and tracked panel remain fixed; only
    oxygen availability changes.  The final answer identifies the new positive
    co-product supported by the accumulated comparison.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission12 = '12' in self.missions_activated

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
            title='Mission 12',
            width=1280,
        )

        if not is_mission12_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 12 is locked. Complete Mission 11 before comparing constraint-driven byproduct fingerprints.',
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
            theme=mytheme, title='Mission 12 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION12_METHOD} with objective {MISSION12_TARGET_OBJECTIVE}, keep all genes active and {MISSION12_GLUCOSE_REACTION} at its default bound, track ' + ', '.join(MISSION12_REQUIRED_TRACKED_FLUXES) + f', then compare the fully default medium with a second run in which only the lower bound of {MISSION12_OXYGEN_REACTION} is closed.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 12 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: make the two runs identical in method, objective, genes, glucose supply and tracked panel. Oxygen availability must be the only changed condition, so any target or co-product difference can be attributed to that constraint.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 12 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: a constraint is binding when it removes possibilities needed by the previous optimum. Compare both the target flux and the complete byproduct fingerprint before deciding what changed.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 12 Briefing', width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Almeida now wants a controlled comparison rather than a single fingerprint. Configure the model to maximise predicted {MISSION12_TARGET_PRODUCT} secretion and record a complete target/byproduct panel under two oxygen conditions.

            Keep the strain and modelling question unchanged. The two visible runs must differ only in oxygen availability. Determine whether the environmental constraint changes the theoretical target maximum and identify the new positive co-product that appears.

            Both direct product-optimal solutions may predict no growth. Treat them as theoretical optima under this model and these bounds, not as viable production-strain claims.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        panel_text = '   '.join(
            f"{MISSION12_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
            for reaction_id in MISSION12_REQUIRED_TRACKED_FLUXES
        )
        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 12: Constraint-Driven Succinate Byproducts',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Record two complete succinate-optimal fingerprints with identical settings except for oxygen availability, then identify the new positive co-product.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Target/byproduct panel:\n{panel_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=25,
            padding=(5, 0, 0, 40),
        )
        menu.add.button('Mission 12 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission12:
            report = load_mission12_byproduct_check()
            menu.add.label(
                build_mission12_comparison_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'New anaerobic co-product: ',
                default='',
                input_underline='_',
                maxchar=30,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission12, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission12(self):
        if not is_mission12_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 11 before starting Mission 12.', time=3000)
            return
        if '12' in self.missions_completed:
            self.mission12 = True
            animation_text_save('Mission 12 is already completed.', time=2500)
            return
        if '12' in self.missions_activated:
            self.mission12 = True
            animation_text_save('Mission 12 is already active.', time=2500)
            return

        clear_mission12_byproduct_check()
        self.mission12 = True
        if '12' not in self.missions_activated:
            self.missions_activated.insert(0, '12')
        animation_text_save('Mission 12 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission12_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 11 first!', time=2500)
            return
        if '12' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 12 before delivering results.', time=3000)
            return

        report = load_mission12_byproduct_check()
        if not report or report.get('mission_id') != '12' or report.get('check_version') != MISSION12_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Build the controlled Mission 12 comparison first.', time=3000)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            animation_text_save('Record both complete visible fingerprints before submitting the co-product.', time=3200)
            return
        if normalise_mission12_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter the new co-product name or its exchange-reaction id.', time=3000)
            return
        if not mission12_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That co-product is not supported by the recorded comparison.', time=3200)
            return

        self.success.play()
        if '12' not in self.missions_completed:
            self.missions_completed.insert(0, '12')
        animation_text_save('Congratulations! Mission 12 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()
