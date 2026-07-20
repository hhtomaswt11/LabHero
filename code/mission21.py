import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from utils import *
from mission22 import Mission22_info
from mission23 import Mission23_info
from mission24 import Mission24_info
from mission25 import Mission25_info
from simulation import (
    MISSION21_METHOD,
    MISSION21_GROWTH_OBJECTIVE,
    MISSION21_OXYGEN_REACTION,
    MISSION21_MIN_GROWTH_DROP,
)


class Mission21:
    """Mission 21 — Controlled Comparison.

    First Dr. Vega mission and first mission of Lab 5: Comparative Experiment Lab.
    The player learns to compare two simulations instead of judging one run alone.
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

        self.menu21 = Mission21_info(self.toggle_menu, self.player)
        self.menu22 = Mission22_info(self.toggle_menu, self.player)
        self.menu23 = Mission23_info(self.toggle_menu, self.player)
        self.menu24 = Mission24_info(self.toggle_menu, self.player)
        self.menu25 = Mission25_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        intro21_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Vega.",
            "This lab is about comparing experiments, not only running one simulation.",
            "Let's start with a controlled comparison: normal oxygen vs no oxygen."
        ]

        active21_dialogue = [
            "Mission 21 is active. Run two controlled simulations.",
            "First run the normal baseline. Then change only oxygen availability.",
            "Use Compare Runs in New Results to interpret the difference."
        ]

        intro22_dialogue = [
            f"Good first comparison, {self.player.player_name}.",
            "Now compare two strains instead of two environments.",
            "Keep everything the same, then test one gene knockout."
        ]

        active22_dialogue = [
            "Mission 22 is active. Compare normal strain vs one knockout.",
            "Track ethanol in Production Flux for both runs.",
            "Then use Compare Runs to see if production improved."
        ]

        intro23_dialogue = [
            f"Strong work, {self.player.player_name}.",
            "Now compare two objectives instead of two environments or strains.",
            "Same setup, different objective: growth versus ethanol production."
        ]

        active23_dialogue = [
            "Mission 23 is active. Compare biomass objective vs ethanol objective.",
            "Keep the strain and environment unchanged in both runs.",
            "Track ethanol and use Compare Runs to inspect the objective trade-off."
        ]

        intro24_dialogue = [
            f"Excellent comparison, {self.player.player_name}.",
            "You showed that changing the objective changes what the model optimizes.",
            "Now compare two simulation methods while keeping the setup unchanged."
        ]

        active24_dialogue = [
            "Mission 24 is active. Compare FBA with pFBA.",
            "Keep objective, genes and environment the same in both runs.",
            "Track the same production fluxes and use Compare Runs."
        ]

        intro25_dialogue = [
            f"Great work, {self.player.player_name}.",
            "You compared environments, genes, objectives and methods.",
            "For my final task, prepare a complete controlled comparison report."
        ]

        active25_dialogue = [
            "Mission 25 is active. Build a final controlled report.",
            "Compare aerobic baseline vs oxygen-limited growth again, but now track the full product panel.",
            "Use Compare Runs to show both growth and production-profile changes."
        ]

        completed25_dialogue = [
            f"Excellent work, {self.player.player_name}.",
            "You completed Dr. Vega's controlled-comparison sequence.",
            "You are ready for Dr. Sato and sensitivity experiments."
        ]

        self.input()
        if '25' in self.missions_completed:
            self.menu_message(completed25_dialogue, buttons=False)
        elif '25' in self.missions_activated:
            self.menu_message(active25_dialogue, menu_to_open=self.menu25)
        elif '24' in self.missions_completed:
            self.menu_message(intro25_dialogue, menu_to_open=self.menu25)
        elif '24' in self.missions_activated:
            self.menu_message(active24_dialogue, menu_to_open=self.menu24)
        elif '23' in self.missions_completed:
            self.menu_message(intro24_dialogue, menu_to_open=self.menu24)
        elif '23' in self.missions_activated:
            self.menu_message(active23_dialogue, menu_to_open=self.menu23)
        elif '22' in self.missions_completed:
            self.menu_message(intro23_dialogue, menu_to_open=self.menu23)
        elif '22' in self.missions_activated:
            self.menu_message(active22_dialogue, menu_to_open=self.menu22)
        elif '21' in self.missions_completed:
            self.menu_message(intro22_dialogue, menu_to_open=self.menu22)
        elif '21' in self.missions_activated:
            self.menu_message(active21_dialogue, menu_to_open=self.menu21)
        else:
            self.menu_message(intro21_dialogue, menu_to_open=self.menu21)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        imagem_path = get_resource_path('graphics/dialogues/vega.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        if imagem.get_size() != (150, 150):
            imagem = pygame.transform.smoothscale(imagem, (150, 150))
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render('Dr. Vega', True, 'black')
        self.screen.blit(nome, (52, 677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                target_menu = menu_to_open or self.menu21
                self.pending = target_menu.update

            botao_teste = Button(200, 650, 150, 50, self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()


class Mission21_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)

        self.mission21 = '21' in self.missions_activated

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
            title='Mission 21',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 21 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 21: Controlled Comparison.

            Lab 5 introduces comparative experiments. Instead of checking only one
            simulation result, you will compare two runs side by side.

            Run A should be the baseline: normal medium, no gene knockouts,
            {MISSION21_METHOD}, and the biomass objective.

            Run B should change only one variable: oxygen availability.
            Close the lower bound of {MISSION21_OXYGEN_REACTION} and run the simulation again.

            After the second run, open Compare Runs in New Results and check how growth changed.
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
            'Mission 21: Controlled Comparison',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Vega wants a simple controlled comparison.

            Compare normal aerobic growth with oxygen-limited growth.
            The goal is not to find a new strain; the goal is to compare two runs.

            Run A — baseline:
            - Method: {MISSION21_METHOD}
            - Objective: {MISSION21_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: unchanged

            Run B — modified setup:
            - Method: {MISSION21_METHOD}
            - Objective: {MISSION21_GROWTH_OBJECTIVE}
            - Genes: no knockouts
            - Environment: close only the lower bound of {MISSION21_OXYGEN_REACTION}

            After the second simulation, open New Results -> Compare Runs.
            Growth should decrease by at least {MISSION21_MIN_GROWTH_DROP:.1f}.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 21 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission21:
            menu.add.button('Deliver Comparison Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission21, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission21(self):
        clear_compare_runs()
        clear_mission21_comparison_check()
        self.mission21 = True
        if '21' not in self.missions_activated:
            self.missions_activated.insert(0, '21')
        animation_text_save('Mission 21 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission21_comparison_check()

        if (not report_data
                or report_data.get('mission_id') != '21'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 21 comparison first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '21' not in self.missions_completed:
                self.missions_completed.insert(0, '21')
            animation_text_save('Congratulations! Mission 21 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('baseline_run_found'):
            animation_text_save('Missing baseline. Run normal FBA with biomass objective first.', time=3000)
        elif not report_data.get('oxygen_limited_run_found'):
            animation_text_save('Missing modified run. Close only the oxygen lower bound and run again.', time=3000)
        elif not report_data.get('growth_decreased'):
            animation_text_save('The comparison does not show a clear growth decrease yet.', time=3000)
        else:
            animation_text_save('Almost there. Open Compare Runs and check the controlled comparison.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
