import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from simulation import VILLAIN_SCORE, CHALLENGE_GROWTH_OBJECTIVE, CHALLENGE_PRODUCTION_OBJECTIVE


class Mission06:
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

        self.menu = Mission06_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        self.m06_step1 = [
            f"Welcome back, {self.player.player_name}! I'm Dr. Carter, and I have a final challenge for you.",
            "A rival scientist claims he has a better E. coli strain for ethanol production.",
            "Can you balance growth and production to beat the rival strain?"
        ]

        self.m06_step2 = [
            "Did you already run the challenge simulation?",
            "Remember: the best strain needs growth and ethanol production, not just one of them."
        ]

        self.m06_step3 = [
            "You optimized the strain... but did you optimize your trust?",
            "Sometimes the villain is closer than you think.",
            "Like hidden pathways in metabolism,",
            "some identities only reveal themselves after the right reaction."
        ]

        self.input()
        if '06' in self.missions_completed:
            self.menu_message(self.m06_step3, buttons=False)

        elif '06' in self.missions_activated:
            self.menu_message(self.m06_step2)

        else:
            self.menu_message(self.m06_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        if '06' in self.missions_completed:
            imagem_path = get_resource_path('graphics/dialogues/carter_malefico.jpg')
            npc_name = 'Dr. Carter?'
        else:
            imagem_path = get_resource_path('graphics/dialogues/carter.jpg')
            npc_name = 'Dr. Carter'

        imagem = pygame.image.load(imagem_path).convert()
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render(npc_name, True, 'black')
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


class Mission06_info:
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

        if '06' in self.missions_activated:
            self.mission06 = True
        else:
            self.mission06 = False

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
            title='Mission 06',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 06 Briefing',
            width=1280
        )

        menu_text.add.label(
            """
            Welcome to the Growth vs Production Challenge.

            A rival scientist has created an E. coli strain that produces ethanol while still growing.
            To beat the rival strain, you must configure our E. coli using what you learned before:
            environmental conditions and gene knockouts.

            Target product: ethanol
            Production reaction: EX_etoh_e
            Growth objective: BIOMASS_Ecoli_core_w_GAM

            Your score is calculated automatically after each simulation:
            score = growth x ethanol production flux
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
            Task 1 - Configure E. coli:
            Go to the simulation computer and change environmental conditions and/or gene knockouts.

            Task 2 - Run the simulation:
            The normal simulation result will still appear, but Mission 06 also calculates a challenge score.

            Task 3 - Balance growth and production:
            A high growth value with no ethanol production is not enough.
            High ethanol production with no growth is also not enough.
            You need a good balance between both.

            Task 4 - Beat the rival strain:
            Villain score: {VILLAIN_SCORE:.3f}
            After you get a higher score, return to Dr. Carter and deliver the challenge results.

            Note:
            The challenge ignores the objective selected in the normal simulation menu.
            It always runs FBA with biomass as the objective and then reads ethanol production from that same solution:
            - growth objective = {CHALLENGE_GROWTH_OBJECTIVE}
            - production flux = {CHALLENGE_PRODUCTION_OBJECTIVE}
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
            "Mission 06: Growth vs Production Challenge",
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34
        )

        menu.add.label(
            f"""
            A rival scientist is trying to beat our lab with a better ethanol-producing E. coli strain.

            Your goal is to configure E. coli and get a higher score than the villain.

            Target product: ethanol ({CHALLENGE_PRODUCTION_OBJECTIVE})
            Score formula: growth x ethanol production flux
            Villain score: {VILLAIN_SCORE:.3f}
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30
        )

        menu.add.button('Mission 06 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission06:
            menu.add.button('Deliver Challenge Results', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission06, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)

        await run_menu(menu, self.display_surface)

    def toggle_menu(self):
        self.toggle_talk = not self.toggle_talk

    def activate_mission06(self):
        self.mission06 = True
        if '06' not in self.missions_activated:
            self.missions_activated.insert(0, '06')
        animation_text_save('Mission 06 Activated')

    def deliver_results(self):
        challenge_data = load_challenge_score()

        if not challenge_data:
            self.failed.play()
            animation_text_save('Run a Mission 06 challenge simulation first!', time=2500)
            return

        try:
            score = float(challenge_data.get('score', 0))
        except Exception:
            score = 0

        if score > VILLAIN_SCORE:
            self.success.play()
            if '06' not in self.missions_completed:
                self.missions_completed.insert(0, '06')
            animation_text_save('Congratulations! You beat the villain score!', time=2500)
            save_file([self.player.player_name, self.player.results, self.player.missions_activated, self.player.missions_completed])
        else:
            self.failed.play()
            animation_text_save('Not enough... Try to improve your growth-production balance!', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback

    async def update(self):
        self.input()
        await self.setup()
