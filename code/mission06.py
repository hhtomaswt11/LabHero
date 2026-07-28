import pygame
import pygame_menu

from async_menu import run_menu
from button import Button
from functions import animation_text_save
from options_values import mytheme
from save_load import clear_challenge_score, load_challenge_score, save_file
from settings import *
from simulation import (
    MISSION06_CANDIDATE_GENES,
    MISSION06_GENE_NAMES,
    MISSION06_GROWTH_OBJECTIVE,
    MISSION06_MAX_KNOCKOUTS,
    MISSION06_METHOD,
    MISSION06_MIN_GROWTH_RATIO,
    MISSION06_TARGET_FLUX,
    MISSION06_VILLAIN_SCORE,
    build_mission06_challenge_report_text,
    is_mission06_unlocked,
)
from timers import Timer
from utils import get_resource_path


class Mission06:
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
        self.menu = Mission06_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'Complete Dr. Silva\'s context-dependent production investigation first.',
            'Mission 06 combines the genetic and environmental reasoning developed through Mission 05.',
        ]
        step1 = [
            f"Welcome, {self.player.player_name}. I'm Dr. Carter, and I have a competitive strain-design challenge.",
            'The rival balances growth and ethanol production under a strict genetic budget.',
            'Can you beat the rival without changing or enriching the medium?',
        ]
        step2 = [
            'Have you recorded a clean aerobic reference and tested valid one- or two-gene designs?',
            'Your best valid design is retained, so a weaker later attempt will not erase it.',
        ]
        step3 = [
            'As you have seen, more changes do not always mean better results.',
            'You optimized the strain... but did you optimize your trust?',
            'Sometimes the villain is closer than you think.',
            'Like hidden pathways in metabolism,',
            'some identities only reveal themselves after the right reaction.',
        ]

        self.input()
        if not is_mission06_unlocked(self.missions_completed):
            self.menu_message(locked, buttons=False)
        elif '06' in self.missions_completed:
            self.menu_message(step3, buttons=False)
        elif '06' in self.missions_activated:
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

        if '06' in self.missions_completed:
            image_path = get_resource_path('graphics/dialogues/carter_malefico.jpg')
            npc_name = 'Dr. Carter?'
        else:
            image_path = get_resource_path('graphics/dialogues/carter.jpg')
            npc_name = 'Dr. Carter'

        image = pygame.image.load(image_path).convert()
        self.screen.blit(image, (25, 520))
        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = self.font_nome.render(npc_name, True, 'black')
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


class Mission06_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission06 = '06' in self.missions_activated

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
            title='Mission 06',
            width=1280,
        )

        if not is_mission06_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 06 is locked. Complete Mission 05 with Dr. Silva before entering Dr. Carter\'s multi-knockout challenge.',
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
            theme=mytheme, title='Mission 06 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION06_METHOD} with {MISSION06_GROWTH_OBJECTIVE}, keep the default aerobic medium unchanged, track {MISSION06_TARGET_FLUX}, and test at most {MISSION06_MAX_KNOCKOUTS} highlighted genes per design.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 06 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: first record an all-genes-active reference. Then compare single knockouts with two-gene combinations and verify that the second change genuinely improves the balance index.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 06 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: one knockout may create ethanol secretion while a second changes energy distribution, but every additional restriction can also reduce growth.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 06 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            The rival submitted a strain that combines predicted growth with ethanol secretion. You have a limited genetic budget and may not enrich or otherwise alter the default aerobic medium.

            The game uses a balance index equal to growth multiplied by ethanol secretion from the same biomass-optimal FBA solution. This index is a competition rule, not a universal biological unit.

            A design must retain at least {MISSION06_MIN_GROWTH_RATIO * 100:.0f}% of the all-genes-active reference growth. The best valid attempt is preserved even if you later test a weaker or invalid design.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidate_text = '   '.join(
            f"{gene_id} ({MISSION06_GENE_NAMES.get(gene_id, '')})"
            for gene_id in MISSION06_CANDIDATE_GENES
        )

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 06: Controlled Multi-Knockout Challenge',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            f"""
            Beat the rival balance index while using the unchanged default aerobic medium.

            Candidate genes:
            {candidate_text}

            Genetic budget: at most {MISSION06_MAX_KNOCKOUTS} knockouts per design
            Target flux: {MISSION06_TARGET_FLUX}
            Rival balance index: {MISSION06_VILLAIN_SCORE:.3f}
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=29,
        )
        menu.add.button('Mission 06 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission06:
            report = load_challenge_score()
            menu.add.label(
                build_mission06_challenge_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=23,
            )
            menu.add.vertical_margin(20)
            menu.add.button('Deliver Best Valid Design', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission06, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission06(self):
        if not is_mission06_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 05 before starting Mission 06.', time=3000)
            return
        clear_challenge_score()
        self.mission06 = True
        if '06' not in self.missions_activated:
            self.missions_activated.insert(0, '06')
        animation_text_save('Mission 06 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report = load_challenge_score()
        if not report or report.get('mission_id') != '06' or report.get('check_version') != 3:
            self.failed.play()
            animation_text_save('Record a controlled Mission 06 reference and design attempt first!', time=3000)
            return
        if not report.get('baseline_recorded'):
            self.failed.play()
            animation_text_save('Record the all-genes-active default aerobic reference first.', time=3000)
            return
        best = report.get('best_attempt') or {}
        if not best:
            self.failed.play()
            animation_text_save('No valid knockout design has been recorded yet.', time=2800)
            return
        if not report.get('win'):
            self.failed.play()
            animation_text_save('Your best valid balance index has not beaten the rival yet.', time=3000)
            return

        self.success.play()
        if '06' not in self.missions_completed:
            self.missions_completed.insert(0, '06')
        animation_text_save('Congratulations! You beat the rival with a valid strain design!', time=2800)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
