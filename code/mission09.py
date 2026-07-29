import pygame
import pygame_menu

from async_menu import run_menu
from functions import animation_text_save
from options_values import mytheme
from save_load import clear_mission09_design_check, load_mission09_design_check, save_file
from settings import *
from simulation import (
    MISSION09_CANDIDATE_GENES,
    MISSION09_CHECK_VERSION,
    MISSION09_GENE_NAMES,
    MISSION09_GROWTH_OBJECTIVE,
    MISSION09_METHOD,
    MISSION09_REPLACEMENT_CARBON_SOURCE,
    MISSION09_REPLACEMENT_SOURCE_NAME,
    MISSION09_TARGET_FLUX,
    MISSION09_TARGET_PRODUCT,
    build_mission09_evidence_report_text,
    is_mission09_unlocked,
    mission09_answer_matches,
    normalise_mission09_answer,
)
from timers import Timer
from utils import get_resource_path


class Mission09_info:
    """Mission 09 — Integrated Environment-and-Gene Design."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission09 = '09' in self.missions_activated

        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 09', width=1280,
        )

        if not is_mission09_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 09 is locked. Complete Mission 08 before combining environmental and genetic design.',
                wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        hint3 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 09 Hint 3', width=1280)
        hint3.add.label(
            f'Technical hint: use {MISSION09_METHOD} with {MISSION09_GROWTH_OBJECTIVE}, replace glucose with {MISSION09_REPLACEMENT_CARBON_SOURCE}, keep oxygen available, track {MISSION09_TARGET_FLUX}, record an all-genes-active reference, and then test one highlighted gene per run.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 09 Hint 2', width=1280)
        hint2.add.label(
            'Experimental hint: first create a reference in which L-malate truly replaces glucose. Keep every other condition fixed, then isolate one genetic perturbation at a time and compare both growth and formate.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 09 Hint 1', width=1280)
        hint1.add.label(
            'Conceptual hint: the highest product value is not automatically the best strain. An integrated design must be evaluated against the same environmental reference and retain sufficient predicted growth.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 09 Briefing', width=1280)
        briefing.add.label(
            f"""
            Dr. Nova now combines the concepts from the previous missions. The culture must use {MISSION09_REPLACEMENT_SOURCE_NAME} instead of glucose, while a single genetic intervention is evaluated for growth-coupled {MISSION09_TARGET_PRODUCT} secretion.

            Build a controlled no-knockout reference and compare the highlighted candidates. A useful design must produce the target in the same biomass-optimal solution used to assess growth; direct product maximisation and hidden secondary simulations are not part of this experiment.
            """,
            max_char=-1, wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidate_text = '   '.join(f"{g} ({MISSION09_GENE_NAMES.get(g, '')})" for g in MISSION09_CANDIDATE_GENES)
        menu.add.vertical_margin(20)
        menu.add.label('Mission 09: Integrated Environment-and-Gene Design', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            f"""
            A culture is being redesigned to grow on {MISSION09_REPLACEMENT_SOURCE_NAME} instead of glucose. Determine which single genetic intervention provides the strongest useful {MISSION09_TARGET_PRODUCT} secretion while preserving most of the reference growth.

            Candidate genes:
            {candidate_text}
            """,
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=29,
        )
        menu.add.button('Mission 09 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission09:
            menu.add.label(
                build_mission09_evidence_report_text(load_mission09_design_check()),
                wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20), background_color='white', font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input('Integrated design gene: ', default='', input_underline='_', maxchar=24, onreturn=self.deliver_results)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission09, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission09(self):
        if not is_mission09_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 08 before starting Mission 09.', time=3000)
            return
        clear_mission09_design_check()
        self.mission09 = True
        if '09' not in self.missions_activated:
            self.missions_activated.insert(0, '09')
        animation_text_save('Mission 09 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission09_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 08 first!', time=2500)
            return
        report = load_mission09_design_check()
        if not report or report.get('mission_id') != '09' or report.get('check_version') != MISSION09_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Build the controlled Mission 09 evidence first.', time=3000)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            if not report.get('baseline_recorded'):
                animation_text_save('The no-knockout L-malate reference is still missing.', time=3200)
            elif report.get('missing_candidates'):
                animation_text_save(f"Candidate screen incomplete: {report.get('valid_trial_count', 0)}/{report.get('required_trial_count', 0)} recorded.", time=3300)
            else:
                animation_text_save('The evidence does not identify one unique viable integrated design.', time=3300)
            return
        if normalise_mission09_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter a candidate gene id or gene name from the mission list.', time=3000)
            return
        if not mission09_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That conclusion is not supported by the recorded growth and formate evidence.', time=3300)
            return

        self.success.play()
        if '09' not in self.missions_completed:
            self.missions_completed.insert(0, '09')
        animation_text_save('Congratulations! Mission 09 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()
