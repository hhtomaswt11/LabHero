import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from mission08 import Mission08_info
from mission09 import Mission09_info
from mission10 import Mission10_info
from utils import *
from simulation import (
    MISSION07_TARGET_OBJECTIVE,
    MISSION07_TARGET_PRODUCT,
    MISSION07_DEFAULT_OBJECTIVE,
    MISSION08_TARGET_PRODUCT,
    MISSION09_TARGET_PRODUCT,
    MISSION10_TARGET_PRODUCT,
)


class Mission07:
    """Mission 07 — Objective Matters.

    This is the first mission of the new Advanced Strain Design laboratory.
    It teaches that the objective function selected in FBA changes what the
    model tries to optimise.
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
            "Until now, you changed nutrients, genes and environmental conditions.",
            "Now you will learn why the objective function matters in FBA."
        ]

        self.m07_step2 = [
            "Mission 07 is active. Go to the simulation computer.",
            f"Redirect the model toward {MISSION07_TARGET_PRODUCT} production without changing the strain.",
            "Keep the environment controlled and use the results to guide your conclusion."
        ]

        self.m07_step3 = [
            "Excellent. You saw that changing the objective changes what the model optimizes.",
            "But objective choice is only one part of strain design.",
            "Now let's add environmental constraints to the problem."
        ]

        self.m08_step1 = [
            "Mission 08 is active. This time, the objective is only part of the answer.",
            f"Make {MISSION08_TARGET_PRODUCT} production work under a biologically meaningful constraint.",
            "Keep the strain unchanged and let the simulations guide your reasoning."
        ]

        self.m08_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You now understand that objectives and constraints must work together.",
            "Now combine objective, environment and one knockout in a single design."
        ]

        self.m09_step1 = [
            "Mission 09 is active. This integrated design needs three decisions.",
            f"Target {MISSION09_TARGET_PRODUCT} using objective, environment and exactly one knockout.",
            "Use New Results as feedback until the integrated design is ready."
        ]

        self.m09_step2 = [
            f"Outstanding, {self.player.player_name}.",
            "You combined objective choice, environmental constraints and a useful knockout.",
            "One final Nova challenge remains: robust design with a knockout pair."
        ]

        self.m10_step1 = [
            "Mission 10 is active. This is my hardest challenge yet.",
            f"Target {MISSION10_TARGET_PRODUCT} using objective choice, environment and exactly two knockouts.",
            "Use production-flux evidence and New Results until the robust design is ready."
        ]

        self.m10_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You completed objective choice, constraints, single knockout and double knockout design.",
            "The Advanced Strain Design Lab is complete."
        ]

        self.input()
        if '10' in self.missions_completed:
            self.menu_message(self.m10_step2, buttons=False)
        elif '09' in self.missions_completed and '10' in self.missions_activated:
            self.menu_message(self.m10_step1, target_mission='10')
        elif '09' in self.missions_completed:
            self.menu_message(self.m09_step2, target_mission='10')
        elif '08' in self.missions_completed and '09' in self.missions_activated:
            self.menu_message(self.m09_step1, target_mission='09')
        elif '08' in self.missions_completed:
            self.menu_message(self.m08_step2, target_mission='09')
        elif '07' in self.missions_completed and '08' in self.missions_activated:
            self.menu_message(self.m08_step1, target_mission='08')
        elif '07' in self.missions_completed:
            self.menu_message(self.m07_step3, target_mission='08')
        elif '07' in self.missions_activated:
            self.menu_message(self.m07_step2)
        else:
            self.menu_message(self.m07_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, target_mission='07'):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        imagem_path = get_resource_path('graphics/dialogues/nova.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        if imagem.get_size() != (150, 150):
            imagem = pygame.transform.smoothscale(imagem, (150, 150))
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render('Dr. Nova', True, 'black')
        self.screen.blit(nome, (55, 677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                if target_mission == '10':
                    mission10_menu = Mission10_info(self.toggle_menu, self.player)
                    self.pending = mission10_menu.update
                elif target_mission == '09':
                    mission09_menu = Mission09_info(self.toggle_menu, self.player)
                    self.pending = mission09_menu.update
                elif target_mission == '08':
                    mission08_menu = Mission08_info(self.toggle_menu, self.player)
                    self.pending = mission08_menu.update
                else:
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

        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)

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
            f"""
            Mission 07 Briefing

            In Flux Balance Analysis, the objective function represents the goal that the model is trying to optimize.
            A biomass objective asks a growth question. A product-oriented objective asks a production question.

            Target product: {MISSION07_TARGET_PRODUCT}

            Keep this experiment controlled: do not use gene knockouts or environmental changes.
            Your task is to compare simulation goals and decide when the model is prioritizing the requested product.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
        )
        menu_text.add.label(
            """Study focus:""",
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
            """
            - What biological question is the simulation answering?
            - Is the model still optimizing growth, or has the goal changed?
            - Did the strain and environment remain unchanged?
            - Does the output support your conclusion?
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
            'Mission 07: Objective Matters',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            The goal is to prove that changing the simulation goal changes the result.

            Target product: {MISSION07_TARGET_PRODUCT}

            Keep the strain and environment unchanged.
            Run controlled tests with different simulation goals, compare the results, and deliver your conclusion.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 07 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission07:
            menu.add.button('Deliver Objective Results', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission07, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)

        await run_menu(menu, self.display_surface)

    def activate_mission07(self):
        self.mission07 = True
        if '07' not in self.missions_activated:
            self.missions_activated.insert(0, '07')
        animation_text_save('Mission 07 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        objective_data = load_mission07_objective_check()

        if not objective_data:
            self.failed.play()
            animation_text_save('Run a Mission 07 simulation first!', time=2500)
            return

        if objective_data.get('ready_to_deliver'):
            self.success.play()
            if '07' not in self.missions_completed:
                self.missions_completed.insert(0, '07')
            animation_text_save('Congratulations! Mission Completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not objective_data.get('objective_correct'):
            animation_text_save(f'The selected objective is not targeting {MISSION07_TARGET_PRODUCT} yet.', time=3000)
        elif objective_data.get('environment_changed'):
            animation_text_save('Keep environmental conditions unchanged for this mission!', time=3000)
        elif objective_data.get('knocked_out_genes'):
            animation_text_save('Do not use gene knockouts in Mission 07!', time=3000)
        else:
            animation_text_save('Run the objective simulation again and check the result!', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback

    async def update(self):
        self.input()
        await self.setup()
