import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from mission24 import Mission24_info
from utils import *
from simulation import (
    MISSION23_METHOD,
    MISSION23_BASELINE_OBJECTIVE,
    MISSION23_TARGET_OBJECTIVE,
    MISSION23_TARGET_PRODUCT,
    MISSION23_TARGET_FLUX,
    MISSION23_MIN_PRODUCTION_INCREASE,
)


class Mission23:
    """Dr. Luna's two-mission sensitivity sequence (Missions 23 and 24)."""

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

        self.menu23 = Mission23_info(self.toggle_menu, self.player)
        self.menu24 = Mission24_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        intro23_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Luna.",
            "Dr. Vega showed that two interventions can share one observed phenotype.",
            "Now we will study how predicted responses change across controlled perturbations."
        ]
        active23_dialogue = [
            "Mission 23 is active. Build the controlled comparison described in the briefing.",
            "Keep every unrelated variable fixed and use the visible evidence.",
            "Return with the supported interpretation when the report is complete."
        ]
        intro24_dialogue = [
            f"Good work, {self.player.player_name}.",
            "You completed the first Luna comparison.",
            "Mission 24 will extend the same laboratory with a second controlled analysis."
        ]
        active24_dialogue = [
            "Mission 24 is active. Follow the shared protocol and isolate its intended factor.",
            "Use the complete visible result rather than a single summary value.",
            "Deliver only after the comparison evidence is complete."
        ]
        completed24_dialogue = [
            f"Excellent analysis, {self.player.player_name}.",
            "You completed Dr. Luna's two missions.",
            "Dr. Smith will continue the campaign in Mission 25."
        ]

        self.input()
        if '24' in self.missions_completed:
            self.menu_message(completed24_dialogue, buttons=False)
        elif '24' in self.missions_activated:
            self.menu_message(active24_dialogue, menu_to_open=self.menu24)
        elif '23' in self.missions_completed:
            self.menu_message(intro24_dialogue, menu_to_open=self.menu24)
        elif '23' in self.missions_activated:
            self.menu_message(active23_dialogue, menu_to_open=self.menu23)
        else:
            self.menu_message(intro23_dialogue, menu_to_open=self.menu23)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image_path = get_resource_path('graphics/dialogues/luna.jpg')
        image = pygame.image.load(image_path).convert()
        if image.get_size() != (150, 150):
            image = pygame.transform.smoothscale(image, (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = self.font_nome.render('Dr. Luna', True, 'black')
        self.screen.blit(name, (52, 677))

        for line, message_line in enumerate(message):
            message_line = prepare_dialogue_text(message_line, self.player.player_name)
            surface = self.font.render(message_line, True, 'black')
            self.screen.blit(surface, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                target_menu = menu_to_open or self.menu23
                self.pending = target_menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission23_info:
    """Mission 23 — Objective Comparison.

    First Dr. Luna mission in the revised campaign ownership.  Its scientific
    protocol will be audited independently before manual validation.
    """

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)

        self.mission23 = '23' in self.missions_activated

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
            title='Mission 23',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 23 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Mission 23: Objective Comparison.

            In the previous missions you compared environment and gene changes.
            Now compare the effect of changing only the simulation objective.

            The objective tells the model what it is trying to maximize.
            If the objective is biomass, the model prioritizes growth.
            If the objective is {MISSION23_TARGET_FLUX}, the model prioritizes
            {MISSION23_TARGET_PRODUCT} secretion.

            Keep method, genes and environment unchanged in both runs.
            Track {MISSION23_TARGET_FLUX} in Production Flux so the comparison
            shows the product change clearly.
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
            'Mission 23: Objective Comparison',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Luna now wants an objective-function comparison.

            Question:
            What changes when the same cell is optimized for growth versus
            optimized for {MISSION23_TARGET_PRODUCT} production?

            Run A — growth objective:
            - Method: {MISSION23_METHOD}
            - Objective: {MISSION23_BASELINE_OBJECTIVE}
            - Genes: no knockouts
            - Environment: unchanged
            - Production Flux: track {MISSION23_TARGET_FLUX}

            Run B — product objective:
            - Method: {MISSION23_METHOD}
            - Objective: {MISSION23_TARGET_OBJECTIVE}
            - Genes: no knockouts
            - Environment: unchanged
            - Production Flux: track {MISSION23_TARGET_FLUX}

            After the second simulation, open New Results -> Compare Runs.
            {MISSION23_TARGET_PRODUCT.capitalize()} should increase by at least
            {MISSION23_MIN_PRODUCTION_INCREASE:.1f} when the product objective is used.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 23 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission23:
            menu.add.button('Deliver Objective Comparison', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            if '22' in self.missions_completed:
                menu.add.button('Activate Mission', action=self.activate_mission23, background_color=(50, 100, 100))
            else:
                menu.add.label('Complete Mission 22 before activating this mission.', font_color=(150, 40, 40))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission23(self):
        if '22' not in self.missions_completed:
            self.failed.play()
            animation_text_save('Complete Mission 22 first.', time=2500)
            return

        clear_compare_runs()
        clear_mission23_comparison_check()
        self.mission23 = True
        if '23' not in self.missions_activated:
            self.missions_activated.insert(0, '23')
        animation_text_save('Mission 23 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission23_comparison_check()

        if (not report_data
                or report_data.get('mission_id') != '23'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 23 comparison first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '23' not in self.missions_completed:
                self.missions_completed.insert(0, '23')
            animation_text_save('Congratulations! Mission 23 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('growth_objective_run_found'):
            animation_text_save('Missing Run A. Use biomass objective with unchanged setup.', time=3000)
        elif not report_data.get('product_objective_run_found'):
            animation_text_save(f'Missing Run B. Use {MISSION23_TARGET_OBJECTIVE} as objective.', time=3000)
        elif not report_data.get('target_flux_tracked'):
            animation_text_save(f'Track {MISSION23_TARGET_FLUX} in Production Flux for both runs.', time=3000)
        elif not report_data.get('production_increased'):
            animation_text_save('The product objective has not increased ethanol enough yet.', time=3000)
        else:
            animation_text_save('Almost there. Open Compare Runs and check the objective comparison.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
