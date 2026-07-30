import pygame
import pygame_menu

from async_menu import run_menu
from button import Button
from functions import animation_text_save
from options_values import mytheme
from save_load import (
    clear_mission03_gene_screen_check,
    load_mission03_gene_screen_check,
    save_file,
)
from settings import *
from simulation import (
    MISSION03_CANDIDATE_GENES,
    MISSION03_GENE_NAMES,
    build_mission03_evidence_report_text,
    is_mission03_unlocked,
    mission03_answer_matches,
    normalise_mission03_answer,
)
from timers import Timer
from utils import get_resource_path, prepare_dialogue_text
from mission04 import Mission04_info
from mission05 import Mission05_info


class Mission03:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu

        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.font_nome = pygame.font.Font(font_path, 24)
        self.screen = pygame.display.get_surface()
        self.timer = Timer(200)
        self.menu = Mission03_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'Dr. Martinez is still guiding the environmental investigation.',
            'Complete Mission 02 before moving from environmental tests to gene perturbations.',
        ]
        step1 = [
            f"Greetings {self.player.player_name}! I'm Dr. Silva.",
            'A genetic alteration has compromised predicted growth in one of our E. coli cultures.',
            'Can you use the candidate evidence to identify the conditionally essential gene?',
        ]
        step2 = [
            'Have you built a viable reference and isolated each candidate knockout?',
            'Show me the evidence and the conclusion supported by the growth ratios.',
        ]
        step3 = [
            'Very good! You identified conditional gene essentiality from controlled evidence.',
            'Knockouts are not only used to study growth loss.',
            'They can also redirect metabolism toward useful products. Let us go further.',
        ]
        step4 = [
            'Did you already test the production knockout?',
            'Keep the environmental conditions unchanged and isolate the genetic change.',
        ]
        step5 = [
            'Excellent! You redirected metabolism in aerobic conditions.',
            'Now combine a knockout with an environmental change.',
            'What can E. coli produce without oxygen?',
        ]
        step6 = [
            'Did you manage to combine both variables?',
            'Let me see the evidence you obtained.',
        ]
        step7 = [
            f'Excellent work, {self.player.player_name}!',
            'You now understand conditional essentiality, production knockouts,',
            'and how environment changes metabolic-engineering strategies.',
        ]

        self.input()
        if not is_mission03_unlocked(self.missions_completed):
            self.menu_message(locked, buttons=False)
        elif '03' in self.missions_completed and '04' in self.missions_completed and '05' in self.missions_completed:
            self.menu_message(step7, buttons=False)
        elif '03' in self.missions_completed and '04' in self.missions_completed and '05' in self.missions_activated:
            self.menu_message(step6, target_mission='05')
        elif '03' in self.missions_completed and '04' in self.missions_completed:
            self.menu_message(step5, target_mission='05')
        elif '03' in self.missions_completed and '04' in self.missions_activated:
            self.menu_message(step4, target_mission='04')
        elif '03' in self.missions_completed:
            self.menu_message(step3, target_mission='04')
        elif '03' in self.missions_activated:
            self.menu_message(step2)
        else:
            self.menu_message(step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, target_mission='03'):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image_path = get_resource_path('graphics/dialogues/silva.jpg')
        image = pygame.image.load(image_path).convert()
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = self.font_nome.render('Dr. Silva', True, 'black')
        self.screen.blit(name, (55, 677))

        for line, msg in enumerate(message):
            msg = prepare_dialogue_text(msg, self.player.player_name)
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                if target_mission == '04':
                    self.pending = Mission04_info(self.toggle_menu, self.player).update
                elif target_mission == '05':
                    self.pending = Mission05_info(self.toggle_menu, self.player).update
                else:
                    self.pending = self.menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission03_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission03 = '03' in self.missions_activated

        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)
        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 03',
            width=1280,
        )

        if not is_mission03_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 03 is locked. Complete Mission 02 with Dr. Martinez before beginning the genetic investigation.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 03 Briefing',
            width=1280,
        )

        hint3 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 03 Hint 3', width=1280)
        hint3.add.label(
            'Technical hint: use FBA with the biomass objective and the unchanged default medium. Record one run with every gene active, then switch off exactly one highlighted candidate per run.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20)
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 03 Hint 2', width=1280)
        hint2.add.label(
            'Experimental hint: isolate one genetic perturbation at a time. Several simultaneous knockouts cannot reveal which gene caused the observed change.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20)
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 03 Hint 1', width=1280)
        hint1.add.label(
            'Conceptual hint: the impact of a knockout needs a viable all-genes-active reference. Keep the biological context comparable so the growth difference can be attributed to the gene.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20)
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing.add.label(
            """
            Gene essentiality in a constraint-based model is conditional: it depends on the model, medium, constraints and objective used in the experiment.

            Build evidence that isolates the effect of each candidate gene. Begin from a viable reference, compare each perturbation under the same biological context and use relative predicted growth to distinguish redundant, growth-limiting and operationally essential genes.

            Gene-protein-reaction rules may represent alternative genes or multi-gene complexes. Removing one gene therefore disables a reaction only when the complete rule can no longer be satisfied.

            For this mission, a knockout at or below 1% of the reference growth is treated as operationally essential. This is a mission criterion, not a universal biological definition.
            """,
            max_char=-1, wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20)
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidate_text = '   '.join(
            f"{gene_id} ({MISSION03_GENE_NAMES.get(gene_id, '')})"
            for gene_id in MISSION03_CANDIDATE_GENES
        )
        menu.add.vertical_margin(20)
        menu.add.label('Mission 03: The Conditional Essentiality Screen', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            f"""
            A genetic alteration has compromised predicted E. coli growth. Determine which candidate gene is indispensable for biomass formation in the laboratory's usual model conditions.

            Candidate genes:
            {candidate_text}

            Construct a defensible comparison, inspect the relative growth evidence and submit the candidate supported by the complete screen.
            """,
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=29
        )
        menu.add.button('Mission 03 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission03:
            report = load_mission03_gene_screen_check()
            menu.add.label(
                build_mission03_evidence_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=23,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'Conditionally essential gene: ',
                default='',
                input_underline='_',
                maxchar=24,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission03, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission03(self):
        if not is_mission03_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 02 before starting Mission 03.', time=3000)
            return
        if '03' in self.missions_completed:
            self.mission03 = True
            animation_text_save('Mission 03 is already completed.', time=2500)
            return
        if '03' in self.missions_activated:
            self.mission03 = True
            animation_text_save('Mission 03 is already active.', time=2500)
            return

        clear_mission03_gene_screen_check()
        self.mission03 = True
        if '03' not in self.missions_activated:
            self.missions_activated.insert(0, '03')
        animation_text_save('Mission 03 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission03_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 02 before delivering Mission 03.', time=3000)
            return
        if '03' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 03 before delivering results.', time=3000)
            return
        report = load_mission03_gene_screen_check()
        if not report or report.get('mission_id') != '03' or report.get('check_version') != 2:
            self.failed.play()
            animation_text_save('Build the controlled gene-knockout evidence before delivering.', time=3300)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            baseline = report.get('baseline_recorded')
            missing = report.get('missing_candidates') or []
            if not baseline:
                animation_text_save('A viable all-genes-active reference is still missing.', time=3200)
            elif missing:
                animation_text_save(
                    f"Gene screen incomplete: {report.get('valid_trial_count', 0)}/{report.get('required_trial_count', 0)} candidates recorded.",
                    time=3400,
                )
            else:
                animation_text_save('Review the controlled evidence before delivering.', time=3000)
            return
        if normalise_mission03_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter a candidate gene id or gene name from the mission list.', time=3000)
            return
        if not mission03_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That conclusion is not supported by the recorded growth ratios.', time=3200)
            return

        self.success.play()
        if '03' not in self.missions_completed:
            self.missions_completed.insert(0, '03')
        animation_text_save('Congratulations! Mission 03 completed!', time=2500)
        save_file(self.player.get_save_data())

    def check_results(self, answer):
        return mission03_answer_matches(answer, load_mission03_gene_screen_check())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
