import pygame
import pygame_menu

from async_menu import run_menu
from button import Button
from functions import animation_text_save
from options_values import mytheme
from save_load import (
    clear_mission04_production_check,
    load_mission04_production_check,
    save_file,
)
from settings import *
from simulation import (
    MISSION04_CANDIDATE_GENES,
    MISSION04_GENE_NAMES,
    MISSION04_PRODUCT_NAME,
    build_mission04_evidence_report_text,
    is_mission04_unlocked,
    mission04_answer_matches,
    normalise_mission04_answer,
)
from timers import Timer
from utils import get_dialogue_portrait, get_dialogue_text_surface, get_resource_path, prepare_dialogue_text


class Mission04:
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
        self.menu = Mission04_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'First establish how individual gene knockouts affect predicted growth.',
            'Complete Mission 03 before beginning the production-knockout investigation.',
        ]
        step1 = [
            f'Excellent progress, {self.player.player_name}.',
            'A knockout can do more than reduce growth: it may redirect metabolic flux.',
            'Can you identify a viable genetic perturbation that forces ethanol secretion?',
        ]
        step2 = [
            'Have you built a no-knockout reference and compared every candidate?',
            'A useful design must show product evidence, not only lower growth.',
        ]
        step3 = [
            'Excellent. You identified growth-coupled product formation from controlled evidence.',
            'The medium stayed aerobic, but the knockout changed respiratory capacity.',
            'Next we will combine genetic and environmental constraints.',
        ]

        self.input()
        if not is_mission04_unlocked(self.missions_completed):
            self.menu_message(locked, buttons=False)
        elif '04' in self.missions_completed:
            self.menu_message(step3, buttons=False)
        elif '04' in self.missions_activated:
            self.menu_message(step2)
        else:
            self.menu_message(step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image_path = get_resource_path('graphics/dialogues/silva.jpg')
        image = get_dialogue_portrait(image_path)
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_nome, 'Dr. Silva')
        self.screen.blit(name, (55, 677))

        for line, msg in enumerate(message):
            msg = prepare_dialogue_text(msg, self.player.player_name)
            surf = get_dialogue_text_surface(self.font, msg)
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                self.pending = self.menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission04_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission04 = '04' in self.missions_activated

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
            title='Mission 04',
            width=1280,
        )

        if not is_mission04_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 04 is locked. Complete Mission 03 with Dr. Silva before investigating production knockouts.',
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
            theme=mytheme, title='Mission 04 Hint 3', width=1280,
        )
        hint3.add.label(
            'Technical hint: use FBA with biomass as the objective, keep the default environment unchanged, track EX_etoh_e in Production Flux, record a no-knockout reference and then test exactly one highlighted candidate per run.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 04 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: compare each candidate with the same viable reference. A lower growth value alone is not proof that carbon was redirected to ethanol; inspect the product flux directly.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 04 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: look for growth-coupled production—a perturbation that causes ethanol secretion while the model still predicts viable growth in the same environment.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 04 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Knockouts do not automatically create a useful production strain. A perturbation may have no apparent effect, may reduce growth without redirecting flux, or may force secretion of a target product while preserving some predicted growth.

            Investigate {MISSION04_PRODUCT_NAME} formation in the laboratory's usual aerobic model conditions. Build a controlled comparison that separates the effect of each candidate gene from environmental or objective changes.

            This mission evaluates product secretion in a biomass-optimal solution. It does not ask for the theoretical maximum ethanol yield. The useful design must therefore combine product evidence with continued predicted growth.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidate_text = '   '.join(
            f"{gene_id} ({MISSION04_GENE_NAMES.get(gene_id, '')})"
            for gene_id in MISSION04_CANDIDATE_GENES
        )

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 04: Growth-Coupled Ethanol Production',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            f"""
            The culture retains its usual aerobic medium, but we want to know whether one genetic perturbation can redirect growth-optimal metabolism toward ethanol secretion.

            Candidate genes:
            {candidate_text}

            Construct a defensible comparison and identify the candidate that increases ethanol secretion without eliminating predicted growth.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=29,
        )
        menu.add.button('Mission 04 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission04:
            report = load_mission04_production_check()
            menu.add.label(
                build_mission04_evidence_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=23,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'Production knockout: ',
                default='',
                input_underline='_',
                maxchar=24,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission04, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission04(self):
        if not is_mission04_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 03 before starting Mission 04.', time=3000)
            return
        if '04' in self.missions_completed:
            self.mission04 = True
            animation_text_save('Mission 04 is already completed.', time=2500)
            return
        if '04' in self.missions_activated:
            self.mission04 = True
            animation_text_save('Mission 04 is already active.', time=2500)
            return

        clear_mission04_production_check()
        self.mission04 = True
        if '04' not in self.missions_activated:
            self.missions_activated.insert(0, '04')
        animation_text_save('Mission 04 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission04_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 03 before delivering Mission 04.', time=3000)
            return
        if '04' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 04 before delivering results.', time=3000)
            return
        report = load_mission04_production_check()
        if not report or report.get('mission_id') != '04' or report.get('check_version') != 2:
            self.failed.play()
            animation_text_save('Build the controlled production-knockout evidence before delivering.', time=3300)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            if not report.get('baseline_recorded'):
                animation_text_save('A viable no-knockout production reference is still missing.', time=3200)
            elif report.get('missing_candidates'):
                animation_text_save(
                    f"Production screen incomplete: {report.get('valid_trial_count', 0)}/{report.get('required_trial_count', 0)} candidates recorded.",
                    time=3400,
                )
            elif not report.get('winner_unique'):
                animation_text_save('The recorded evidence does not identify one unique viable production design.', time=3300)
            else:
                animation_text_save('Review the growth and ethanol evidence before delivering.', time=3000)
            return
        if normalise_mission04_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter a candidate gene id or gene name from the mission list.', time=3000)
            return
        if not mission04_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That conclusion is not supported by the recorded growth and ethanol evidence.', time=3300)
            return

        self.success.play()
        if '04' not in self.missions_completed:
            self.missions_completed.insert(0, '04')
        animation_text_save('Congratulations! Mission 04 completed!', time=2500)
        save_file(self.player.get_save_data())

    def check_results(self, answer):
        return mission04_answer_matches(answer, load_mission04_production_check())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
