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
from simulation import (
    MISSION16_METHOD,
    MISSION16_GROWTH_OBJECTIVE,
    MISSION16_BLOCKED_CARBON_SOURCE,
    MISSION16_CANDIDATE_CARBON_SOURCES,
    MISSION16_MIN_GROWTH,
    MISSION17_TARGET_NUTRIENT_NAME,
    MISSION18_EXPORT_BOTTLENECK_NAME,
    MISSION19_TARGET_METHOD,
    MISSION19_TARGET_GENE,
    MISSION19_TARGET_GENE_NAME,
    MISSION20_TARGET_METHOD,
    MISSION20_ALTERNATIVE_CARBON_SOURCE,
    MISSION20_EXPORT_BOTTLENECK_NAME,
)
from mission17 import Mission17_info
from mission18 import Mission18_info
from mission19 import Mission19_info
from mission20 import Mission20_info


class Mission16:
    """Mission 16 — Alternative Carbon Rescue.

    First mission for Dr. Rio. This professor focuses on medium engineering:
    what the cell can import from the environment and how uptake constraints
    shape growth.
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

        self.menu = Mission16_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        self.m16_step1 = [
            f"Hello {self.player.player_name}. I'm Dr. Rio, and I study medium engineering.",
            "Dr. Almeida taught you to read flux evidence.",
            "Now let's test what the model needs to import from the environment."
        ]

        self.m16_step2 = [
            "Mission 16 is active. Rescue growth with an alternative carbon source.",
            "Do not treat this as a genetic problem.",
            "Use the Medium Report in New Results to diagnose uptake from the medium."
        ]

        self.m16_step3 = [
            f"Excellent work, {self.player.player_name}.",
            "You proved that the medium is part of the metabolic design.",
            "Now let's test whether every medium component is optional."
        ]

        self.m17_step1 = [
            "Mission 17 is active. Test an essential medium component.",
            f"Focus on {MISSION17_TARGET_NUTRIENT_NAME} availability and growth response.",
            "Use the Medium Report to connect nutrient removal with viability."
        ]

        self.m17_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You showed that growth depends on more than carbon availability.",
            "Some medium components are essential building blocks for the cell."
        ]

        self.m18_step1 = [
            f"Great progress, {self.player.player_name}.",
            "You have tested carbon sources and essential nutrients.",
            "Now let's test what happens when an export route becomes a bottleneck."
        ]

        self.m18_step2 = [
            f"Mission 18 is active. Constrain {MISSION18_EXPORT_BOTTLENECK_NAME} export.",
            "Use both Medium Report and Production Flux evidence.",
            "Keep the strain unchanged and check that growth remains viable."
        ]

        self.m18_step3 = [
            f"Excellent work, {self.player.player_name}.",
            "You showed that exchange bounds can control both uptake and secretion.",
            "Now let's test how the model responds to a genetic perturbation."
        ]

        self.m19_step1 = [
            "Mission 19 is active. Use a perturbation-response method.",
            f"Select {MISSION19_TARGET_METHOD}, keep the medium unchanged, and test one gene.",
            "Use Production Flux evidence to diagnose the mutant response."
        ]

        self.m19_step2 = [
            f"Excellent perturbation analysis, {self.player.player_name}.",
            f"You used {MISSION19_TARGET_METHOD} to study a single-gene response.",
            "One final Dr. Rio robustness challenge remains."
        ]

        self.m20_step1 = [
            "Mission 20 is active. Build a final medium-robustness report.",
            f"Use {MISSION20_TARGET_METHOD}, test {MISSION20_ALTERNATIVE_CARBON_SOURCE} uptake,",
            f"and verify the {MISSION20_EXPORT_BOTTLENECK_NAME} export bottleneck with flux evidence."
        ]

        self.m20_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You completed the Dr. Rio medium-engineering path.",
            "Your designs now connect medium constraints, method choice and exchange-flux evidence."
        ]

        self.input()
        if '20' in self.missions_completed:
            self.menu_message(self.m20_step2, buttons=False)
        elif '19' in self.missions_completed and '20' in self.missions_activated:
            self.menu_message(self.m20_step1, target_mission='20')
        elif '19' in self.missions_completed:
            self.menu_message(self.m19_step2, target_mission='20')
        elif '18' in self.missions_completed and '19' in self.missions_activated:
            self.menu_message(self.m19_step1, target_mission='19')
        elif '18' in self.missions_completed:
            self.menu_message(self.m18_step3, target_mission='19')
        elif '17' in self.missions_completed and '18' in self.missions_activated:
            self.menu_message(self.m18_step2, target_mission='18')
        elif '17' in self.missions_completed:
            self.menu_message(self.m18_step1, target_mission='18')
        elif '16' in self.missions_completed and '17' in self.missions_activated:
            self.menu_message(self.m17_step1, target_mission='17')
        elif '16' in self.missions_completed:
            self.menu_message(self.m16_step3, target_mission='17')
        elif '16' in self.missions_activated:
            self.menu_message(self.m16_step2)
        else:
            self.menu_message(self.m16_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, target_mission='16'):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        imagem_path = get_resource_path('graphics/dialogues/rio.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        if imagem.get_size() != (150, 150):
            imagem = pygame.transform.smoothscale(imagem, (150, 150))
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render('Dr. Rio', True, 'black')
        self.screen.blit(nome, (56, 677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                if target_mission == '20':
                    mission20_menu = Mission20_info(self.toggle_menu, self.player)
                    self.pending = mission20_menu.update
                elif target_mission == '19':
                    mission19_menu = Mission19_info(self.toggle_menu, self.player)
                    self.pending = mission19_menu.update
                elif target_mission == '18':
                    mission18_menu = Mission18_info(self.toggle_menu, self.player)
                    self.pending = mission18_menu.update
                elif target_mission == '17':
                    mission17_menu = Mission17_info(self.toggle_menu, self.player)
                    self.pending = mission17_menu.update
                else:
                    self.pending = self.menu.update

            botao_teste = Button(200, 650, 150, 50, self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()


class Mission16_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)

        self.mission16 = '16' in self.missions_activated

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
            title='Mission 16',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 16 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 16: Alternative Carbon Rescue.

            Previous missions changed objectives, knockouts and production evidence.
            This mission focuses on the medium: what the model is allowed to import.

            In constraint-based modelling, exchange reactions connect the cell to the environment.
            A negative exchange flux usually means uptake, while a positive flux usually means secretion.

            Use the Medium Report to check whether the original carbon source is blocked
            and whether a new carbon source is actually being consumed by the model.
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
            'Mission 16: Alternative Carbon Rescue',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Dr. Rio medium-engineering challenge.

            Design a controlled medium where E. coli can still grow after losing access
            to its usual carbon source.

            Keep the strain unchanged and use the growth objective.

            Original carbon source to remove:
            {MISSION16_BLOCKED_CARBON_SOURCE}

            Candidate alternative carbon sources:
            {'  '.join(MISSION16_CANDIDATE_CARBON_SOURCES)}

            Find one alternative source that rescues growth and prove it with the Medium Report.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 16 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission16:
            menu.add.button('Deliver Medium Report', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission16, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission16(self):
        clear_mission16_medium_report_check()
        self.mission16 = True
        if '16' not in self.missions_activated:
            self.missions_activated.insert(0, '16')
        animation_text_save('Mission 16 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        report_data = load_mission16_medium_report_check()

        if (not report_data
                or report_data.get('mission_id') != '16'
                or report_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 16 simulation first!', time=2500)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '16' not in self.missions_completed:
                self.missions_completed.insert(0, '16')
            animation_text_save('Congratulations! Mission 16 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('method_correct'):
            animation_text_save('Use FBA for this medium baseline.', time=3000)
        elif not report_data.get('objective_correct'):
            animation_text_save('Use the biomass objective to test growth rescue.', time=3000)
        elif report_data.get('knocked_out_genes'):
            animation_text_save('Do not use gene knockouts for this medium challenge.', time=3000)
        elif not report_data.get('glucose_lower_bound_closed'):
            animation_text_save('The original carbon source is still available.', time=3000)
        elif report_data.get('unexpected_environment_changes'):
            animation_text_save('Too many medium changes. Keep the design controlled.', time=3000)
        elif not report_data.get('exactly_one_alternative_source'):
            animation_text_save('Open exactly one candidate alternative carbon source.', time=3000)
        elif not report_data.get('source_uptake_detected'):
            animation_text_save('The selected source is not being consumed enough yet.', time=3000)
        elif not report_data.get('growth_ok'):
            animation_text_save(f"Growth is still too low. Keep it above {MISSION16_MIN_GROWTH:.1f}.", time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 16 Medium Report to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
