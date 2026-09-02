import pygame
import pygame_menu

from answer_penalty import penalize_wrong_answer

from async_menu import run_menu
from functions import animation_text_save
from hint_ui import MissionHintAccess
from options_values import mytheme
from save_load import clear_mission10_robust_design_check, load_mission10_robust_design_check, save_file
from settings import *
from simulation import (
    MISSION10_CANDIDATE_GENES,
    MISSION10_CHECK_VERSION,
    MISSION10_COMPETING_FLUX,
    MISSION10_GENE_NAMES,
    MISSION10_GROWTH_OBJECTIVE,
    MISSION10_METHOD,
    MISSION10_OXYGEN_REACTION,
    MISSION10_REQUIRED_PAIRS,
    MISSION10_TARGET_FLUX,
    build_mission10_evidence_report_text,
    is_mission10_unlocked,
    mission10_answer_matches,
    normalise_mission10_answer,
)
from timers import Timer
from utils import get_resource_path


class Mission10_info:
    """Mission 10 — Two-Gene Redundancy and Flux Redirection."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission10 = '10' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '10', self.missions_completed, mytheme)

        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 10', width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('10'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 10 is locked. Complete Mission 09 before beginning the two-gene redundancy investigation.',
                wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        hint3 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 10 Hint 3', width=1280, overflow=(False, True))
        hint3.add.label(
            f'Technical hint: use {MISSION10_METHOD} with {MISSION10_GROWTH_OBJECTIVE}, keep the default glucose supply, close only the lower bound of {MISSION10_OXYGEN_REACTION}, track {MISSION10_TARGET_FLUX} and {MISSION10_COMPETING_FLUX}, record a no-knockout reference, then test every listed two-gene pair.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 10 Hint 2', width=1280, overflow=(False, True))
        hint2.add.label(
            'Experimental hint: keep the objective, environment and tracked fluxes identical. Reset all genes between runs, then disable exactly two highlighted candidates so each pair is isolated.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 10 Hint 1', width=1280, overflow=(False, True))
        hint1.add.label(
            'Conceptual hint: in an OR-type GPR, eliminating one gene may leave the reaction functional through an alternative gene. A carefully chosen pair can reveal a phenotype that neither single knockout would produce.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 10 Briefing', width=1280, overflow=(False, True))
        briefing.add.label(
            """
            Dr. Nova's final challenge investigates genetic redundancy. Some reactions remain active after one knockout because an alternative gene satisfies the same OR-type GPR.

            Build a controlled anaerobic reference, compare all listed two-gene pairs, and determine which pair redirects flux from acetate toward ethanol while preserving sufficient predicted growth. Growth, ethanol and acetate must all come from the same visible biomass-optimal solution.
            """,
            max_char=-1, wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidate_text = '   '.join(
            f"{gene_id} ({MISSION10_GENE_NAMES.get(gene_id, '')})" for gene_id in MISSION10_CANDIDATE_GENES
        )
        pair_text = '\n'.join(
            '- ' + ' + '.join(f"{gene_id} ({MISSION10_GENE_NAMES.get(gene_id, '')})" for gene_id in pair)
            for pair in MISSION10_REQUIRED_PAIRS
        )
        menu.add.vertical_margin(20)
        menu.add.label('Mission 10: Two-Gene Redundancy and Flux Redirection', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            'Establish a no-knockout anaerobic reference and compare every controlled pair. Identify the pair that most effectively increases ethanol while retaining enough reference growth.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=27,
        )
        menu.add.label(
            f"Candidate genes:\n{candidate_text}\n\nRequired pairs:\n{pair_text}",
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, font_size=27,
            padding=(5, 0, 0, 40),
        )
        menu.add.button('Mission 10 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission10:
            menu.add.label(
                build_mission10_evidence_report_text(load_mission10_robust_design_check()),
                wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20), background_color='white', font_size=21,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input('Winning gene pair: ', default='', input_underline='_', maxchar=40, onreturn=self.deliver_results)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission10, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission10(self):
        if not self.player.is_mission_unlocked('10'):
            self.failed.play()
            animation_text_save('Complete Mission 09 before starting Mission 10.', time=3000)
            return
        if '10' in self.missions_completed:
            self.mission10 = True
            animation_text_save('Mission 10 is already completed.', time=2500)
            return
        if '10' in self.missions_activated:
            self.mission10 = True
            animation_text_save('Mission 10 is already active.', time=2500)
            return

        clear_mission10_robust_design_check()
        self.mission10 = True
        if '10' not in self.missions_activated:
            self.missions_activated.insert(0, '10')
        animation_text_save('Mission 10 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('10'):
            self.failed.play()
            animation_text_save('Complete Mission 09 first!', time=2500)
            return
        if '10' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 10 before delivering results.', time=3000)
            return
        report = load_mission10_robust_design_check()
        if not report or report.get('mission_id') != '10' or report.get('check_version') != MISSION10_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Build the controlled Mission 10 evidence first.', time=3000)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            if not report.get('baseline_recorded'):
                animation_text_save('The no-knockout anaerobic reference is still missing.', time=3200)
            elif report.get('missing_pairs'):
                animation_text_save(f"Pair screen incomplete: {report.get('valid_trial_count', 0)}/{report.get('required_trial_count', 0)} recorded.", time=3300)
            else:
                animation_text_save('The evidence does not identify one unique eligible two-gene design.', time=3300)
            return
        if normalise_mission10_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter two candidate gene ids or gene names from the mission list.', time=3000)
            penalize_wrong_answer(self.player, '10')
            return
        if not mission10_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That pair is not supported by the recorded growth, ethanol and acetate evidence.', time=3300)
            penalize_wrong_answer(self.player, '10')
            return

        self.success.play()
        if '10' not in self.missions_completed:
            self.missions_completed.insert(0, '10')
        animation_text_save('Congratulations! Dr. Nova arc completed!', time=2800)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()
