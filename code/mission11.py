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
    MISSION11_REQUIRED_TRACKED_FLUXES,
    MISSION11_TARGET_CONTEXT,
    MISSION11_GROWTH_OBJECTIVE,
    MISSION11_MIN_POSITIVE_PRODUCTS,
    MISSION12_TARGET_PRODUCT,
)
from mission12 import Mission12_info


class Mission11:
    """Mission 11 — Flux Fingerprint.

    First mission for Dr. Almeida. This professor focuses on flux diagnostics:
    using production-flux evidence to interpret what a simulation is doing,
    rather than only looking at the objective value.
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

        self.menu = Mission11_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        self.m11_step1 = [
            f"Hello {self.player.player_name}. I'm Dr. Almeida, and I study flux diagnostics.",
            "Dr. Nova taught you how to design strains.",
            "Now I want you to prove what the model is actually secreting."
        ]

        self.m11_step2 = [
            "Mission 11 is active. Build a flux fingerprint for the simulation.",
            "Use Production Flux evidence, not only the objective value.",
            "Keep the setup controlled and let New Results guide your diagnosis."
        ]

        self.m11_step3 = [
            "Excellent diagnostic work.",
            "A single objective value never tells the full metabolic story.",
            "Now let's use flux evidence to compare a target product with byproducts."
        ]

        self.m12_step1 = [
            "Mission 12 is active. This time, focus on competing byproducts.",
            f"Prioritize {MISSION12_TARGET_PRODUCT}, but do not ignore what else the model secretes.",
            "Use Production Flux evidence to compare the target with alternative products."
        ]

        self.m12_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You used flux evidence to separate a target product from competing byproducts.",
            "That is the beginning of real pathway diagnosis."
        ]

        self.input()
        if '12' in self.missions_completed:
            self.menu_message(self.m12_step2, buttons=False)
        elif '11' in self.missions_completed and '12' in self.missions_activated:
            self.menu_message(self.m12_step1, target_mission='12')
        elif '11' in self.missions_completed:
            self.menu_message(self.m11_step3, target_mission='12')
        elif '11' in self.missions_activated:
            self.menu_message(self.m11_step2)
        else:
            self.menu_message(self.m11_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, target_mission='11'):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        imagem_path = get_resource_path('graphics/dialogues/rio.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        if imagem.get_size() != (150, 150):
            imagem = pygame.transform.smoothscale(imagem, (150, 150))
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = self.font_nome.render('Dr. Almeida', True, 'black')
        self.screen.blit(nome, (42, 677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                if target_mission == '12':
                    mission12_menu = Mission12_info(self.toggle_menu, self.player)
                    self.pending = mission12_menu.update
                else:
                    self.pending = self.menu.update

            botao_teste = Button(200, 650, 150, 50, self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()


class Mission11_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.timer = Timer(200)

        self.mission11 = '11' in self.missions_activated

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
            title='Mission 11',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 11 Briefing',
            width=1280,
        )

        menu_text.add.label(
            f"""
            Welcome to Mission 11: Flux Fingerprint.

            Dr. Nova's missions focused on choosing and changing the simulation setup.
            This mission focuses on reading the evidence produced by the model.

            A growth value tells you if the strain is viable.
            A production-flux panel tells you what the strain is secreting.

            Diagnostic context: {MISSION11_TARGET_CONTEXT}

            Keep the genetic background unchanged and use the standard biomass objective.
            Build a secretion fingerprint using several production fluxes, then compare the output.
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
            'Mission 11: Flux Fingerprint',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )

        menu.add.label(
            f"""
            Flux diagnostics challenge.

            Build a secretion fingerprint for E. coli under {MISSION11_TARGET_CONTEXT}.

            Keep the biomass objective active.
            Do not use gene knockouts.
            Use one meaningful environmental constraint.

            Production flux panel:
            {'  '.join(MISSION11_REQUIRED_TRACKED_FLUXES)}

            The design is ready when New Results confirms that enough products are being tracked
            and the simulation still represents a viable strain.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )

        menu.add.button('Mission 11 Briefing', menu_text, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(50)

        if self.mission11:
            menu.add.button('Deliver Flux Fingerprint', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission11, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission11(self):
        clear_mission11_flux_fingerprint_check()
        self.mission11 = True
        if '11' not in self.missions_activated:
            self.missions_activated.insert(0, '11')
        animation_text_save('Mission 11 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        fingerprint_data = load_mission11_flux_fingerprint_check()

        if (not fingerprint_data
                or fingerprint_data.get('mission_id') != '11'
                or fingerprint_data.get('check_version') != 1):
            self.failed.play()
            animation_text_save('Run a Mission 11 simulation first!', time=2500)
            return

        if fingerprint_data.get('ready_to_deliver'):
            self.success.play()
            if '11' not in self.missions_completed:
                self.missions_completed.insert(0, '11')
            animation_text_save('Congratulations! Mission 11 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not fingerprint_data.get('method_correct'):
            animation_text_save('Use the standard FBA method for this diagnostic baseline.', time=3000)
        elif not fingerprint_data.get('objective_correct'):
            animation_text_save('Keep the biomass objective active for this fingerprint.', time=3000)
        elif fingerprint_data.get('knocked_out_genes'):
            animation_text_save('Do not use knockouts yet. Keep the strain unchanged.', time=3000)
        elif not fingerprint_data.get('oxygen_lower_bound_closed'):
            animation_text_save('The environment is not respiration-limited yet.', time=3000)
        elif fingerprint_data.get('unexpected_environment_changes'):
            animation_text_save('Too many environmental changes. Keep only the key constraint.', time=3000)
        elif not fingerprint_data.get('tracking_ready'):
            animation_text_save('Production Flux evidence is incomplete. Track the full product panel.', time=3000)
        elif not fingerprint_data.get('positive_products_ready'):
            animation_text_save('The fingerprint is not informative yet. Compare the product fluxes.', time=3000)
        elif not fingerprint_data.get('growth_ok'):
            animation_text_save('Growth is too low. The strain is not viable enough.', time=3000)
        else:
            animation_text_save('Almost there. Use the Mission 11 Flux Fingerprint Check to refine it.', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
