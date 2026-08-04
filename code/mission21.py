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
from simulation import (
    MISSION21_CHECK_VERSION,
    MISSION21_METHOD,
    MISSION21_GROWTH_OBJECTIVE,
    MISSION21_OXYGEN_REACTION,
    MISSION21_ETHANOL_EXPORT,
    MISSION21_REQUIRED_TRACKED_FLUXES,
    build_mission21_compensatory_report_text,
    initialise_mission21_compensatory_comparison,
    is_mission21_unlocked,
    mission21_answer_matches,
    normalise_mission21_answer,
)


class Mission21:
    """Dr. Vega's two-mission controlled-comparison sequence."""

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
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        intro21_dialogue = [
            f"Hello {self.player.player_name}. I'm Dr. Vega.",
            "My lab studies controlled before-and-after comparisons.",
            "Begin by tracing compensation after one active export route is closed."
        ]

        active21_dialogue = [
            "Mission 21 is active. Record the anaerobic reference and modified run.",
            "Change only the ethanol-export upper bound between the two simulations.",
            "Compare the flux differences and submit the secretion with the largest rise."
        ]

        intro22_dialogue = [
            f"Strong comparison, {self.player.player_name}.",
            "You quantified compensation after one export route was removed.",
            "My final task compares two mechanisms under one recorded phenotype panel."
        ]

        active22_dialogue = [
            "Mission 22 is active. Record the environmental and GPR-based genetic interventions.",
            "Keep the shared FBA protocol and complete phenotype panel controlled.",
            "Compare every output difference and submit only the supported count."
        ]

        completed22_dialogue = [
            f"Excellent work, {self.player.player_name}.",
            "Different mechanisms can produce the same recorded phenotype.",
            "Dr. Luna will continue in Mission 23.",
            "Dr. Luna will now study how phenotypes change across perturbation levels."
        ]

        self.input()
        if '22' in self.missions_completed:
            self.menu_message(completed22_dialogue, buttons=False)
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
            msg = prepare_dialogue_text(msg, self.player.player_name)
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
    """Mission 21 — Compensatory Flux Comparison."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission21 = '21' in self.missions_activated

        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 21',
            width=1280,
        )

        if not is_mission21_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 21 is locked. Complete Mission 20 before beginning Dr. Vega\'s comparison laboratory.',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 21 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION21_METHOD}, objective {MISSION21_GROWTH_OBJECTIVE}, every gene active and model-default glucose. Close {MISSION21_OXYGEN_REACTION} uptake in both runs. Track ' + ', '.join(MISSION21_REQUIRED_TRACKED_FLUXES) + f'. In the second run, close only the upper bound of {MISSION21_ETHANOL_EXPORT}.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 21 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: calculate each tracked value as modified minus reference. The requested route is the one with the largest positive difference, not necessarily the largest final value.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 21 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: when an active export route is removed, a viable network may redirect flux through another secretion route. A controlled comparison attributes the change to the single altered bound.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 21 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Vega wants one compact before-and-after comparison.

            Shared protocol:
            Use {MISSION21_METHOD}, the biomass objective, every gene active, model-default glucose and the complete product/byproduct panel. Close oxygen uptake in both runs and keep every unrelated bound at its model default.

            Record two visible runs:
            1. Anaerobic reference: ethanol export upper bound open.
            2. Modified run: close only the upper bound of {MISSION21_ETHANOL_EXPORT}.

            Compare modified minus reference for every tracked secretion. Submit the route with the largest positive increase. The final field expects one concise route, not an essay.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 21: Compensatory Flux Comparison',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Compare an anaerobic reference with the same setup after ethanol export is closed, then identify the largest compensatory secretion increase.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Controlled setup:\nOxygen uptake: {MISSION21_OXYGEN_REACTION} lower bound closed in both runs\nChanged factor: {MISSION21_ETHANOL_EXPORT} upper bound open versus closed\nProduction Flux panel: {", ".join(MISSION21_REQUIRED_TRACKED_FLUXES)}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=24,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 21 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission21:
            report = load_mission21_comparison_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '21'
                or report.get('check_version') != MISSION21_CHECK_VERSION
            ):
                report = initialise_mission21_compensatory_comparison()
            menu.add.label(
                build_mission21_compensatory_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.label(
                'Question: Which tracked secretion showed the largest increase after ethanol export was closed?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Largest increase: ',
                default='',
                input_underline='_',
                maxchar=60,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission21, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission21(self):
        if not is_mission21_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 20 before starting Mission 21.', time=3000)
            return
        if '21' in self.missions_completed:
            return
        if '21' in self.missions_activated:
            self.mission21 = True
            return

        clear_compare_runs()
        clear_mission21_comparison_check()
        initialise_mission21_compensatory_comparison()
        self.mission21 = True
        self.missions_activated.insert(0, '21')
        animation_text_save('Mission 21 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission21_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 20 first!', time=2500)
            return
        if '21' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 21 before delivering a conclusion.', time=2800)
            return

        report = load_mission21_comparison_check()
        if (
            not report
            or report.get('mission_id') != '21'
            or report.get('check_version') != MISSION21_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the two current-format Mission 21 runs first.', time=3000)
            return
        if not report.get('all_runs_recorded'):
            self.failed.play()
            animation_text_save('Record both the anaerobic reference and ethanol-closed run.', time=3000)
            return
        if not report.get('same_controlled_setup'):
            self.failed.play()
            animation_text_save('The two runs do not preserve the controlled setup.', time=3000)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The visible comparison does not support one unique largest secretion increase.', time=3000)
            return
        if len(normalise_mission21_answer(answer)) != 1:
            self.failed.play()
            animation_text_save('Enter exactly one tracked secretion route.', time=2800)
            return
        if not mission21_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That route is not supported by the recorded before-and-after differences.', time=3000)
            return

        self.success.play()
        if '21' not in self.missions_completed:
            self.missions_completed.insert(0, '21')
        animation_text_save('Congratulations! Mission 21 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
