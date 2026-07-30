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
from mission27 import Mission27_info
from mission28 import Mission28_info
from simulation import (
    MISSION26_METHOD,
    MISSION26_GROWTH_OBJECTIVE,
    MISSION26_SWEEP_REACTION,
    MISSION26_SWEEP_BOUND_LABEL,
    MISSION26_SWEEP_VALUES,
    MISSION26_REQUIRED_TRACKED_FLUXES,
    MISSION26_MIN_GROWTH_DROP,
)


class Mission26:
    """Mission 26 — Oxygen Sensitivity Sweep.

    First Dr. Luna mission. This begins the sensitivity block: instead of
    changing a condition only ON/OFF, the player tests several intermediate
    levels and reads the trend.
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

        self.menu26 = Mission26_info(self.toggle_menu, self.player)
        self.menu27 = Mission27_info(self.toggle_menu, self.player)
        self.menu28 = Mission28_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        intro26_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Luna.",
            "Dr. Vega taught you to compare two runs.",
            "Now study sensitivity between fully available and blocked conditions."
        ]

        active26_dialogue = [
            "Mission 26 is active. Build a clean sensitivity experiment.",
            "Choose the environmental variable linked to respiration and test it gradually.",
            "Use the Bound Sweep Report to justify the trend, not just one row."
        ]

        intro27_dialogue = [
            f"Good work, {self.player.player_name}.",
            "Oxygen was the first sensitivity test. Now move beyond an obvious gas switch.",
            "Now study carbon supply, growth collapse and secretion trends."
        ]

        active27_dialogue = [
            "Mission 27 is active. Study limitation of the main carbon supply.",
            "This one needs stronger evidence: multiple tracked products and a clear trend.",
            "Do not just check the final point. Read the whole series."
        ]

        intro28_dialogue = [
            f"Excellent, {self.player.player_name}.",
            "You found how carbon limitation affects both growth and byproduct secretion.",
            "Now combine a controlled medium change with a sweep of another nutrient source."
        ]

        active28_dialogue = [
            "Mission 28 is active. Create a medium where the usual carbon source is unavailable.",
            "Then test one candidate source across several availability levels.",
            "A good source is consumed, supports growth, and becomes limiting when scarce."
        ]

        completed28_dialogue = [
            f"Good analysis, {self.player.player_name}.",
            "You showed that carbon-source availability level matters, not only its presence.",
            "Next, we will push sensitivity testing toward minimal viable conditions."
        ]

        self.input()
        if '28' in self.missions_completed:
            self.menu_message(completed28_dialogue, buttons=False)
        elif '28' in self.missions_activated:
            self.menu_message(active28_dialogue, menu_to_open=self.menu28)
        elif '27' in self.missions_completed:
            self.menu_message(intro28_dialogue, menu_to_open=self.menu28)
        elif '27' in self.missions_activated:
            self.menu_message(active27_dialogue, menu_to_open=self.menu27)
        elif '26' in self.missions_completed:
            self.menu_message(intro27_dialogue, menu_to_open=self.menu27)
        elif '26' in self.missions_activated:
            self.menu_message(active26_dialogue, menu_to_open=self.menu26)
        else:
            self.menu_message(intro26_dialogue, menu_to_open=self.menu26)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        imagem_path = get_resource_path('graphics/dialogues/luna.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        if imagem.get_size() != (150, 150):
            imagem = pygame.transform.smoothscale(imagem, (150, 150))
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render('Dr. Luna', True, 'black')
        self.screen.blit(nome, (52, 677))

        for line, msg in enumerate(message):
            msg = prepare_dialogue_text(msg, self.player.player_name)
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                target_menu = menu_to_open or self.menu26
                self.pending = target_menu.update

            botao_teste = Button(200, 650, 150, 50, self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()


class Mission26_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)

        self.mission26 = '26' in self.missions_activated

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
            title='Mission 26',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 26 Briefing',
            width=1280,
        )

        tracked_flux_text = ', '.join(MISSION26_REQUIRED_TRACKED_FLUXES)
        sweep_values_text = ', '.join(str(value).rstrip('0').rstrip('.') for value in MISSION26_SWEEP_VALUES)

        menu_text.add.label(
            f"""
            Mission 26: Oxygen Sensitivity Sweep.

            A normal comparison only checks two situations. A Bound Sweep tests
            several levels of one bound and asks you to read the trend.

            Dr. Luna wants a clean respiration-sensitivity experiment:
            keep the strain unchanged, use a growth objective, and vary only the
            environmental variable that controls oxygen availability.

            Choose a sweep that moves from oxygen available to oxygen blocked.
            Then compare how growth, uptake and secreted products change across
            the rows.

            Optional hint: in exchange reactions, changing the lower bound changes
            how much of a compound the model can consume from the medium.
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
            'Mission 26: Oxygen Sensitivity Sweep',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Luna wants a sensitivity experiment, not a simple ON/OFF test.

            Question:
            How does E. coli behaviour change when respiration becomes gradually limited?

            Build a controlled setup:
            - use a normal growth-focused simulation
            - keep the strain unchanged
            - avoid extra environmental changes before the sweep
            - track a small product/byproduct panel as evidence

            In Bound Sweep Setup, choose the exchange bound that controls oxygen
            consumption and test a sequence from available to unavailable.

            To pass, the report must show a consistent trend: oxygen uptake falls,
            growth responds, and the secretion profile changes across the sweep.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 26 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission26:
            menu.add.button('Deliver Oxygen Sweep', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            if '25' in self.missions_completed:
                menu.add.button('Activate Mission', action=self.activate_mission26, background_color=(50, 100, 100))
            else:
                menu.add.label('Complete Mission 25 before activating this mission.', font_color=(150, 40, 40))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission26(self):
        if '25' not in self.missions_completed:
            self.failed.play()
            animation_text_save('Complete Mission 25 first.', time=2500)
            return

        clear_bound_sweep()
        clear_mission26_bound_sweep_check()
        self.mission26 = True
        if '26' not in self.missions_activated:
            self.missions_activated.insert(0, '26')
        animation_text_save('Mission 26 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission26_bound_sweep_check()

        if (not report_data
                or report_data.get('mission_id') != '26'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run the Mission 26 Bound Sweep first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '26' not in self.missions_completed:
                self.missions_completed.insert(0, '26')
            animation_text_save('Congratulations! Mission 26 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('clean_base_setup'):
            animation_text_save('Keep the base setup clean: growth objective, no knockouts and no extra medium changes.', time=3000)
        elif not report_data.get('oxygen_sweep_selected'):
            animation_text_save('The sweep variable should control oxygen uptake from the medium.', time=3000)
        elif not report_data.get('all_points_valid'):
            animation_text_save('The sweep is missing valid result points.', time=3000)
        elif not report_data.get('growth_decreased'):
            animation_text_save('Growth did not respond clearly across the respiration sweep.', time=3000)
        elif not report_data.get('oxygen_uptake_decreased'):
            animation_text_save('The tested uptake should decrease across the sweep.', time=3000)
        elif not report_data.get('profile_changed'):
            animation_text_save('The product/byproduct profile has not changed enough yet.', time=3000)
        else:
            animation_text_save('Almost there. Open the Bound Sweep Report and inspect the trend.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
