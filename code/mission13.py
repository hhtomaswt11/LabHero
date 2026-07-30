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
    MISSION13_CHECK_VERSION,
    MISSION13_BASELINE_METHOD,
    MISSION13_TARGET_METHOD,
    MISSION13_TARGET_OBJECTIVE,
    MISSION13_REQUIRED_TRACKED_FLUXES,
    MISSION13_PRODUCT_NAMES,
    build_mission13_parsimony_report_text,
    is_mission13_unlocked,
    mission13_answer_matches,
    normalise_mission13_answer,
)


class Mission13_info:
    """Mission 13 — Primary Objective and Flux Parsimony.

    The player compares one FBA reference with one pFBA run while keeping the
    biological setup fixed.  The final interpretation distinguishes the
    primary reaction objective from pFBA's secondary total-flux criterion.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission13 = '13' in self.missions_activated

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
            title='Mission 13',
            width=1280,
        )

        if not is_mission13_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 13 is locked. Complete Mission 12 before comparing FBA with pFBA.',
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
            theme=mytheme, title='Mission 13 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use objective {MISSION13_TARGET_OBJECTIVE}, close only the lower bound of EX_o2_e, keep all genes active and track ' + ', '.join(MISSION13_REQUIRED_TRACKED_FLUXES) + f'. Record one {MISSION13_BASELINE_METHOD} run and one {MISSION13_TARGET_METHOD} run. The order is irrelevant.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 13 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: method must be the only variable that changes. Compare the primary succinate flux, the complete external fingerprint, biomass, medium uptake, total absolute flux and active-reaction count.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 13 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: pFBA first preserves the primary optimum. Its extra number belongs to a secondary criterion and must not be interpreted as extra product formation.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 13 Briefing', width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Almeida wants a controlled method comparison. Keep the same anaerobic succinate-optimisation problem from Mission 12, but compare {MISSION13_BASELINE_METHOD} with {MISSION13_TARGET_METHOD}.

            Determine what remains unchanged in the primary objective and external exchange fingerprint. Then interpret what the additional pFBA criterion minimises. A lower total flux is possible, but equality is also scientifically valid when the FBA solver already returned a parsimonious optimum.

            Do not use gene knockouts or alter the medium. Every value used in the comparison must come from the two visible solver results.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        panel_text = '   '.join(
            f"{MISSION13_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
            for reaction_id in MISSION13_REQUIRED_TRACKED_FLUXES
        )
        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 13: Primary Objective and Flux Parsimony',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Build a controlled FBA-versus-pFBA comparison and distinguish the primary succinate flux from the secondary parsimony criterion.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Complete exchange panel:\n{panel_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=25,
            padding=(5, 0, 0, 40),
        )
        menu.add.button('Mission 13 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission13:
            report = load_mission13_method_check()
            menu.add.label(
                build_mission13_parsimony_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'pFBA secondary criterion minimises: ',
                default='',
                input_underline='_',
                maxchar=60,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission13, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission13(self):
        if not is_mission13_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 12 before starting Mission 13.', time=3000)
            return
        clear_mission13_method_check()
        self.mission13 = True
        if '13' not in self.missions_activated:
            self.missions_activated.insert(0, '13')
        animation_text_save('Mission 13 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission13_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 12 first!', time=2500)
            return

        report = load_mission13_method_check()
        if not report or report.get('mission_id') != '13' or report.get('check_version') != MISSION13_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Build the controlled Mission 13 comparison first.', time=3000)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            animation_text_save('Record both complete visible method-comparison runs before answering.', time=3200)
            return
        if normalise_mission13_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter the quantity minimised by the pFBA secondary criterion.', time=3000)
            return
        if not mission13_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That answer confuses the primary product objective with the secondary pFBA criterion.', time=3400)
            return

        self.success.play()
        if '13' not in self.missions_completed:
            self.missions_completed.insert(0, '13')
        animation_text_save('Congratulations! Mission 13 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()
