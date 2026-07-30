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
    MISSION11_CHECK_VERSION,
    MISSION11_EXPECTED_DOMINANT_FLUX,
    MISSION11_GROWTH_OBJECTIVE,
    MISSION11_METHOD,
    MISSION11_OXYGEN_REACTION,
    MISSION11_PRODUCT_NAMES,
    MISSION11_REQUIRED_TRACKED_FLUXES,
    MISSION11_TARGET_CONTEXT,
    build_mission11_fingerprint_report_text,
    is_mission11_unlocked,
    mission11_answer_matches,
    normalise_mission11_answer,
    MISSION12_TARGET_PRODUCT,
    MISSION13_TARGET_PRODUCT,
    MISSION13_TARGET_METHOD,
    MISSION14_TARGET_PRODUCT,
    MISSION15_TARGET_PRODUCT,
    MISSION15_TARGET_METHOD,
)
from mission12 import Mission12_info
from mission13 import Mission13_info
from mission14 import Mission14_info
from mission15 import Mission15_info


class Mission11:
    """Mission 11 — Anaerobic Secretion Fingerprint.

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
        locked = [
            'The Flux Diagnostics Lab is still locked.',
            "Complete Dr. Nova's Mission 10 before beginning this laboratory.",
            'Return after finishing the controlled two-gene comparison.',
        ]
        self.m11_step1 = [
            f"Hello {self.player.player_name}. I'm Dr. Almeida, and I study flux diagnostics.",
            "Dr. Nova taught you how to design strains; now you must diagnose their predicted phenotypes.",
            "Start by building and interpreting a complete anaerobic secretion fingerprint.",
        ]

        self.m11_step2 = [
            "Mission 11 is active. Build one controlled anaerobic biomass-optimal fingerprint.",
            "Measure the full product panel in the same visible solution.",
            "Then identify the dominant tracked product from the recorded evidence.",
        ]

        self.m11_step3 = [
            "Excellent diagnostic work.",
            "You distinguished predicted growth from the secretion fingerprint and interpreted the dominant product.",
            "Now use the same evidence discipline to compare a target product with competing byproducts.",
        ]

        self.m12_step1 = [
            "Mission 12 is active. Compare two complete succinate-optimal fingerprints.",
            f"Keep {MISSION12_TARGET_PRODUCT} as the objective and change only oxygen availability.",
            "Use the visible evidence to identify the new co-product introduced by the binding constraint."
        ]

        self.m12_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You showed that a binding environmental constraint can alter both a target maximum and its co-product fingerprint.",
            "Now we can test whether the simulation method changes the diagnosis."
        ]

        self.m13_step1 = [
            "Mission 13 is active. Compare the same product problem with pFBA.",
            f"Target {MISSION13_TARGET_PRODUCT}, but focus on the simulation method this time.",
            "Use Production Flux evidence to support the method comparison."
        ]

        self.m13_step2 = [
            f"Excellent method comparison, {self.player.player_name}.",
            "You distinguished the primary product objective from pFBA's secondary parsimony criterion.",
            "Next, screen genetic interventions without mistaking one lower byproduct for a complete improvement."
        ]

        self.m14_step1 = [
            "Mission 14 is active. Screen every highlighted single-gene intervention.",
            f"Keep {MISSION14_TARGET_PRODUCT} as the primary target and inspect the complete co-product fingerprint.",
            "A negative result is valid when every candidate introduces a trade-off."
        ]

        self.m14_step2 = [
            f"Excellent screening work, {self.player.player_name}.",
            "You showed that reducing acetate alone can create other co-products or sacrifice the target.",
            "One final Dr. Almeida diagnostic challenge will come next."
        ]

        self.m15_step1 = [
            "Mission 15 is active. This is my final diagnostic challenge.",
            f"Build a complete report for {MISSION15_TARGET_PRODUCT} production using {MISSION15_TARGET_METHOD}.",
            "Use method choice, one knockout and full Production Flux evidence."
        ]

        self.m15_step2 = [
            f"Outstanding work, {self.player.player_name}.",
            "You can now design, diagnose and justify metabolic engineering strategies.",
            "This laboratory's flux-diagnostics training is complete."
        ]

        self.input()
        if not is_mission11_unlocked(self.missions_completed):
            self.menu_message(locked, buttons=False)
        elif '15' in self.missions_completed:
            self.menu_message(self.m15_step2, buttons=False)
        elif '14' in self.missions_completed and '15' in self.missions_activated:
            self.menu_message(self.m15_step1, target_mission='15')
        elif '14' in self.missions_completed:
            self.menu_message(self.m14_step2, target_mission='15')
        elif '13' in self.missions_completed and '14' in self.missions_activated:
            self.menu_message(self.m14_step1, target_mission='14')
        elif '13' in self.missions_completed:
            self.menu_message(self.m13_step2, target_mission='14')
        elif '12' in self.missions_completed and '13' in self.missions_activated:
            self.menu_message(self.m13_step1, target_mission='13')
        elif '12' in self.missions_completed:
            self.menu_message(self.m12_step2, target_mission='13')
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

        imagem_path = get_resource_path('graphics/dialogues/almeida.jpg')
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
                if target_mission == '15':
                    mission15_menu = Mission15_info(self.toggle_menu, self.player)
                    self.pending = mission15_menu.update
                elif target_mission == '14':
                    mission14_menu = Mission14_info(self.toggle_menu, self.player)
                    self.pending = mission14_menu.update
                elif target_mission == '13':
                    mission13_menu = Mission13_info(self.toggle_menu, self.player)
                    self.pending = mission13_menu.update
                elif target_mission == '12':
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
    """Mission 11 — Anaerobic Secretion Fingerprint."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission11 = '11' in self.missions_activated

        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 11', width=1280,
        )

        if not is_mission11_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 11 is locked. Complete Mission 10 before beginning Dr. Almeida\'s flux-diagnostics training.',
                wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        hint3 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 11 Hint 3', width=1280)
        hint3.add.label(
            f'Technical hint: use {MISSION11_METHOD} with {MISSION11_GROWTH_OBJECTIVE}, keep all genes active and the default glucose supply unchanged, close only the lower bound of {MISSION11_OXYGEN_REACTION}, and track ' + ', '.join(MISSION11_REQUIRED_TRACKED_FLUXES) + '.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 11 Hint 2', width=1280)
        hint2.add.label(
            'Experimental hint: keep the strain, objective and default carbon supply fixed. Introduce only the anaerobic constraint, then make sure every requested exchange flux is numerically present in the visible result.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 11 Hint 1', width=1280)
        hint1.add.label(
            'Conceptual hint: the biomass objective tells you about the predicted growth optimum. Exchange fluxes answer a separate question: which compounds this particular solution predicts are secreted.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 11 Briefing', width=1280)
        briefing.add.label(
            """
            Dr. Almeida wants a diagnostic fingerprint rather than another strain design. Build one controlled anaerobic solution that still maximises biomass, measure a defined panel of exchange reactions, and distinguish positive predicted secretion from zero flux.

            A positive exchange flux is evidence of secretion in this specific model solution. A zero value does not prove that the organism can never produce the compound; it only describes this objective and these constraints.

            After recording the complete fingerprint, interpret the evidence and submit the dominant tracked product.
            """,
            max_char=-1, wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        panel_text = '   '.join(
            f"{MISSION11_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
            for reaction_id in MISSION11_REQUIRED_TRACKED_FLUXES
        )
        menu.add.vertical_margin(20)
        menu.add.label('Mission 11: Anaerobic Secretion Fingerprint', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            'Generate one complete anaerobic secretion fingerprint from the visible biomass-optimal solution, then identify the dominant tracked product.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=27,
        )
        menu.add.label(
            f'Fingerprint panel:\n{panel_text}',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, font_size=25,
            padding=(5, 0, 0, 40),
        )
        menu.add.button('Mission 11 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission11:
            report = load_mission11_flux_fingerprint_check()
            menu.add.label(
                build_mission11_fingerprint_report_text(report),
                wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20), background_color='white', font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.text_input(
                'Dominant tracked product: ', default='', input_underline='_',
                maxchar=30, onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission11, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission11(self):
        if not is_mission11_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 10 before starting Mission 11.', time=3000)
            return
        clear_mission11_flux_fingerprint_check()
        self.mission11 = True
        if '11' not in self.missions_activated:
            self.missions_activated.insert(0, '11')
        animation_text_save('Mission 11 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission11_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 10 first!', time=2500)
            return

        report = load_mission11_flux_fingerprint_check()
        if not report or report.get('mission_id') != '11' or report.get('check_version') != MISSION11_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Build the controlled Mission 11 fingerprint first.', time=3000)
            return
        if not report.get('evidence_ready'):
            self.failed.play()
            if report.get('current_issues'):
                animation_text_save('The complete visible fingerprint has not been recorded yet.', time=3200)
            else:
                animation_text_save('Run the controlled fingerprint before submitting an interpretation.', time=3200)
            return
        if normalise_mission11_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter the dominant product name or its exchange-reaction id.', time=3000)
            return
        if not mission11_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That product is not supported as dominant by the recorded fingerprint.', time=3200)
            return

        self.success.play()
        if '11' not in self.missions_completed:
            self.missions_completed.insert(0, '11')
        animation_text_save('Congratulations! Mission 11 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()

