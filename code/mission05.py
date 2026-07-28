import pygame
import pygame_menu

from async_menu import run_menu
from button import Button
from functions import animation_text_save
from options_values import mytheme
from save_load import (
    clear_mission05_production_check,
    load_mission05_production_check,
    save_file,
)
from settings import *
from simulation import (
    MISSION05_CANDIDATE_GENES,
    MISSION05_GENE_NAMES,
    MISSION05_PRODUCT_NAME,
    build_mission05_evidence_report_text,
    is_mission05_unlocked,
    mission05_answer_matches,
    normalise_mission05_answer,
)
from timers import Timer
from utils import get_resource_path


class Mission05:
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
        self.menu = Mission05_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'First identify a viable aerobic production knockout.',
            'Complete Mission 04 before testing whether that strategy transfers to anaerobiosis.',
        ]
        step1 = [
            f'Good work, {self.player.player_name}. Your aerobic design forced ethanol secretion.',
            'But genetic strategies are not independent of their environment.',
            'Can you find the strongest viable design after oxygen uptake becomes unavailable?',
        ]
        step2 = [
            'Have you established an anaerobic reference and compared every candidate?',
            'Look for additional ethanol while preserving most of the reference growth.',
        ]
        step3 = [
            'Excellent. You demonstrated that a useful knockout is context-dependent.',
            'The aerobic winner became neutral, while another strategy performed better anaerobically.',
            'Dr. Carter is waiting in the next lab with a broader multi-knockout strain-design challenge.',
        ]

        self.input()
        if not is_mission05_unlocked(self.missions_completed):
            self.menu_message(locked, buttons=False)
        elif '05' in self.missions_completed:
            self.menu_message(step3, buttons=False)
        elif '05' in self.missions_activated:
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
        image = pygame.image.load(image_path).convert()
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = self.font_nome.render('Dr. Silva', True, 'black')
        self.screen.blit(name, (55, 677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                self.pending = self.menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission05_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission05 = '05' in self.missions_activated

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
            title='Mission 05',
            width=1280,
        )

        if not is_mission05_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 05 is locked. Complete Mission 04 with Dr. Silva before comparing production designs in a new environmental context.',
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
            theme=mytheme, title='Mission 05 Hint 3', width=1280,
        )
        hint3.add.label(
            'Technical hint: use FBA with biomass as the objective, make oxygen uptake unavailable while leaving the rest of the default medium unchanged, track EX_etoh_e, record an all-genes-active reference and then test exactly one highlighted candidate per run.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 05 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: compare each candidate with the same anaerobic no-knockout reference. Evaluate both additional ethanol secretion and retained growth.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 05 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: a genetic perturbation that is useful when respiration is available may add nothing once the environment already prevents oxygen uptake.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 05 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Mission 04 identified a genetic perturbation that redirected growth-optimal metabolism toward {MISSION05_PRODUCT_NAME} while oxygen remained available in the medium.

            The culture is now evaluated in an anaerobic environment, where fermentation is already active. Investigate whether the previous strategy still provides an advantage or whether another candidate creates a stronger increase in ethanol while preserving most of the predicted anaerobic growth.

            Build a controlled comparison. The conclusion must be supported by both production and growth evidence under the same environmental constraints.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidate_text = '   '.join(
            f"{gene_id} ({MISSION05_GENE_NAMES.get(gene_id, '')})"
            for gene_id in MISSION05_CANDIDATE_GENES
        )

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 05: Context-Dependent Anaerobic Ethanol Design',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            f"""
            The environmental context has changed: the culture can no longer use oxygen uptake and already depends on fermentation.

            Candidate genes:
            {candidate_text}

            Determine which viable candidate produces the strongest additional ethanol secretion relative to an anaerobic no-knockout reference.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=29,
        )
        menu.add.button('Mission 05 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission05:
            report = load_mission05_production_check()
            menu.add.label(
                build_mission05_evidence_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=23,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'Anaerobic production knockout: ',
                default='',
                input_underline='_',
                maxchar=24,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission05, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission05(self):
        if not is_mission05_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 04 before starting Mission 05.', time=3000)
            return
        clear_mission05_production_check()
        self.mission05 = True
        if '05' not in self.missions_activated:
            self.missions_activated.insert(0, '05')
        animation_text_save('Mission 05 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        report = load_mission05_production_check()
        if not report or report.get('mission_id') != '05' or report.get('check_version') != 2:
            self.failed.play()
            animation_text_save('Build the controlled anaerobic production evidence before delivering.', time=3300)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            if not report.get('baseline_recorded'):
                animation_text_save('A viable anaerobic no-knockout reference is still missing.', time=3200)
            elif report.get('missing_candidates'):
                animation_text_save(
                    f"Anaerobic production screen incomplete: {report.get('valid_trial_count', 0)}/{report.get('required_trial_count', 0)} candidates recorded.",
                    time=3400,
                )
            elif not report.get('winner_unique'):
                animation_text_save('The recorded evidence does not identify one unique viable anaerobic design.', time=3300)
            else:
                animation_text_save('Review the anaerobic growth and ethanol evidence before delivering.', time=3000)
            return
        if normalise_mission05_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter a candidate gene id or gene name from the mission list.', time=3000)
            return
        if not mission05_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That conclusion is not supported by the recorded anaerobic growth and ethanol evidence.', time=3300)
            return

        self.success.play()
        if '05' not in self.missions_completed:
            self.missions_completed.insert(0, '05')
        animation_text_save('Congratulations! Mission 05 completed!', time=2500)
        save_file(self.player.get_save_data())

    def check_results(self, answer):
        return mission05_answer_matches(answer, load_mission05_production_check())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
