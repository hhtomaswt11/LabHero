import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from simulation import (
    MISSION05_PRODUCT_NAME,
    MISSION05_PRODUCTION_OBJECTIVE,
    MISSION05_TARGET_GENE,
    MISSION05_TARGET_GENE_NAME,
    MISSION05_CANDIDATE_GENES,
    MISSION05_OXYGEN_REACTION,
)


class Mission05:
    def __init__(self, toggle_menu, player) -> None:
        # general setup
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
        self.m05_step1 = [
            f"Excellent work, {self.player.player_name}! You redirected metabolism with a knockout.",
            "Now we will combine a genetic change with an environmental change.",
            "Can you improve lactate production when E. coli has no oxygen?"
        ]

        self.m05_step2 = [
            "Did you combine both variables?",
            "Close the O2 lower bound and test one candidate knockout at a time."
        ]

        self.m05_step3 = [
            f"Outstanding work, {self.player.player_name}!",
            "You combined environment and genetics to guide metabolism.",
            "You are ready for harder metabolic engineering challenges."
        ]

        self.input()
        if '05' in self.missions_completed:
            self.menu_message(self.m05_step3, buttons=False)

        elif '05' in self.missions_activated:
            self.menu_message(self.m05_step2)

        else:
            self.menu_message(self.m05_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        imagem_path = get_resource_path('graphics/dialogues/silva.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render('Dr. Silva', True, 'black')
        self.screen.blit(nome, (55, 677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                self.pending = self.menu.update

            botao_teste = Button(200, 650, 150, 50, self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()


class Mission05_info:
    def __init__(self, toggle_menu, player) -> None:
        # general setup
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)

        self.index = 0
        self.timer = Timer(200)

        if '05' in self.missions_activated:
            self.mission05 = True
        else:
            self.mission05 = False

        # sounds
        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)

        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 05',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 05 Briefing',
            width=1280
        )

        candidate_text = '  '.join(MISSION05_CANDIDATE_GENES)

        menu_text.add.label(
            f"""
            Welcome to Mission 05: Knockout for Production under Anaerobic Conditions.

            In Mission 04, you studied one genetic change under normal aerobic conditions.
            Now, you will combine two variables: oxygen availability and a gene knockout.

            Target product: {MISSION05_PRODUCT_NAME}
            Production reaction: {MISSION05_PRODUCTION_OBJECTIVE}
            Environmental change: close the lower bound of {MISSION05_OXYGEN_REACTION}
            Target gene to discover: one of the candidate genes below

            Candidate genes:
            {candidate_text}
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0)
        )
        menu_text.add.label(
            """Tasks:""",
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(100, 0),
            background_color='gold',
            font_color='black',
            font_size=30,
            padding=(25, 25, 25, 25)
        )
        menu_text.add.label(
            f"""
            Task 1 - Create anaerobic conditions:
            Go to Environmental Conditions and close the lower bound of {MISSION05_OXYGEN_REACTION}.
            This prevents E. coli from taking in oxygen.

            Task 2 - Test candidate knockouts:
            Go to Genes and switch off one candidate gene at a time.

            Task 3 - Observe lactate production:
            After each simulation, check the Mission 05 Production Check in New Results.
            Compare the anaerobic baseline with the current lactate flux.

            Task 4 - Report the production gene:
            Return to Dr. Silva and report the gene whose knockout improves lactate production.

            Hint:
            This mission requires both changes: oxygen off and the correct knockout.
            The correct answer is a gene id, like b0000.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0)
        )

        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 05: Anaerobic Production Knockout',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34
        )

        menu.add.label(
            f"""
            This mission combines environment and genetics.

            Target product: {MISSION05_PRODUCT_NAME}
            Production reaction: {MISSION05_PRODUCTION_OBJECTIVE}

            Important rule:
            First close the O2 lower bound. Then test one candidate gene knockout.

            Candidate genes:
            {candidate_text}
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30
        )

        menu.add.button('Mission 05 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission05:
            menu.add.text_input('Production Gene: ', default='', input_underline='_', maxchar=5, onreturn=self.deliver_results)
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission05, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)

        await run_menu(menu, self.display_surface)

    def toggle_menu(self):
        self.toggle_talk = not self.toggle_talk

    def activate_mission05(self):
        self.mission05 = True
        if '05' not in self.missions_activated:
            self.missions_activated.insert(0, '05')
        animation_text_save('Mission 05 Activated')

    def deliver_results(self, ans):
        right = self.check_results(ans)

        if right:
            self.success.play()
            if '05' not in self.missions_completed:
                self.missions_completed.insert(0, '05')
            animation_text_save('Congratulations! Mission Completed!', time=2000)
            save_file([self.player.player_name, self.player.results, self.player.missions_activated, self.player.missions_completed])
        else:
            self.failed.play()
            animation_text_save('No ... Try again!', time=2000)

    def check_results(self, ans):
        answer = str(ans).strip().lower()
        return answer in {MISSION05_TARGET_GENE.lower(), MISSION05_TARGET_GENE_NAME.lower()}

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback

    async def update(self):
        self.input()
        await self.setup()
