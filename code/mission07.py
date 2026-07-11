import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from utils import *


class Mission07:
    """Placeholder mission for the first new laboratory NPC.

    This mission is intentionally simple. Its goal is to test the full
    interaction pipeline for the new Tiled object named Mission07 before we
    implement the real scientific content for this laboratory.
    """

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

        self.menu = Mission07_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        self.m07_step1 = [
            f"Hello {self.player.player_name}! Welcome to the Advanced Strain Design Lab.",
            "This new area will later contain harder metabolic engineering missions.",
            "For now, let's test if this new scientist is correctly connected to the game."
        ]

        self.m07_step2 = [
            "Mission 07 is active. This is only a technical test for now.",
            "Open the mission menu again and complete the test interaction."
        ]

        self.m07_step3 = [
            "Great! The new laboratory interaction is working correctly.",
            "Now this scientist can receive real advanced missions later."
        ]

        self.input()
        if '07' in self.missions_completed:
            self.menu_message(self.m07_step3, buttons=False)
        elif '07' in self.missions_activated:
            self.menu_message(self.m07_step2)
        else:
            self.menu_message(self.m07_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        # Temporary portrait. Replace later when the final NPC portrait is chosen.
        imagem_path = get_resource_path('graphics/dialogues/nova.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render('Dr. Nova', True, 'black')
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


class Mission07_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)

        self.mission07 = '07' in self.missions_activated

        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 07',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 07 Briefing',
            width=1280,
        )

        menu_text.add.label(
            """
            Mission 07 is currently a technical placeholder.

            The purpose of this mission is to confirm that the new scientist placed in Tiled is correctly connected to the game logic.

            Later, this same NPC can be used for advanced strain design missions, such as:
            - choosing metabolic objectives;
            - testing double knockouts;
            - optimizing production while keeping growth above a minimum.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
        )
        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 07: New Laboratory Test',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            """
            This is a temporary test mission for the new scientist.

            If you can activate and complete this mission, then the Mission07 object in Tiled is correctly connected to the code.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 07 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission07:
            menu.add.button('Complete Test Mission', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission07, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)

        await run_menu(menu, self.display_surface)

    def toggle_menu(self):
        self.toggle_talk = not self.toggle_talk

    def activate_mission07(self):
        self.mission07 = True
        if '07' not in self.missions_activated:
            self.missions_activated.insert(0, '07')
        animation_text_save('Mission 07 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        self.success.play()
        if '07' not in self.missions_completed:
            self.missions_completed.insert(0, '07')
        animation_text_save('Mission 07 Test Completed!', time=2000)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
