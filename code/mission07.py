import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from hint_ui import MissionHintAccess
from button import Button
from async_menu import run_menu
from mission08 import Mission08_info
from mission09 import Mission09_info
from mission10 import Mission10_info
from utils import *
from simulation import (
    MISSION07_METHOD,
    MISSION07_BIOMASS_OBJECTIVE,
    MISSION07_TARGET_OBJECTIVE,
    MISSION07_TARGET_PRODUCT,
    MISSION07_TARGET_FLUX,
    MISSION09_TARGET_PRODUCT,
    MISSION10_TARGET_PRODUCT,
    build_mission07_objective_comparison_report_text,
    is_mission07_unlocked,
)


class Mission07:
    """Mission 07 — controlled comparison of FBA objective functions."""

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
        locked = [
            "Complete Dr. Carter's controlled multi-knockout challenge first.",
            'Mission 07 builds on the difference between measuring ethanol and maximising it.',
        ]
        self.m07_step1 = [
            f"Hello {self.player.player_name}! Welcome to Dr. Nova's lab.",
            'Previously, ethanol was measured while biomass remained the objective.',
            'Now compare that with a simulation that directly prioritises ethanol.',
        ]
        self.m07_step2 = [
            'Mission 07 is active. Keep the strain, medium and method unchanged.',
            'Build a controlled comparison in which only the objective function changes.',
            'Use the visible biomass, ethanol and oxygen evidence to interpret both solutions.',
        ]
        self.m07_step3 = [
            'Excellent. You showed that the objective changes the question, not the strain.',
            'Direct product maximisation can yield an optimum with no predicted growth.',
            'Now test whether an environmental restriction must change that optimum.',
        ]

        self.m08_step1 = [
            'Mission 08 is active. Compare D-lactate before and after oxygen is closed.',
            'Do not assume that adding a restriction must change the optimum.',
            'Use product, growth and oxygen fluxes to decide whether the optimum changes.',
        ]
        self.m08_step2 = [
            f'Excellent work, {self.player.player_name}.',
            'Closing oxygen changed nothing because the earlier optimum used no oxygen.',
            'Now integrate a controlled carbon-source change with one genetic perturbation.',
        ]
        self.m09_step1 = [
            'Mission 09 is active. Build an L-malate reference and test each highlighted knockout.',
            f'Track {MISSION09_TARGET_PRODUCT} in the same biomass-optimal solutions used to assess growth.',
            'Use New Results to identify the best balanced integrated design.',
        ]
        self.m09_step2 = [
            f'Great job, {self.player.player_name}.',
            'You combined environmental context, biomass evidence and a helpful knockout.',
            'One final Nova challenge remains: two-gene redundancy and flux redirection.',
        ]
        self.m10_step1 = [
            'Mission 10 is active. This is my hardest challenge yet.',
            f'Use two-gene redundancy to redirect anaerobic flux toward {MISSION10_TARGET_PRODUCT}.',
            'Record every pair, then justify the winner with growth, ethanol and acetate.',
        ]
        self.m10_step2 = [
            f'Excellent work, {self.player.player_name}.',
            'You completed objective choice, constraints, and single- and double-knockout design.',
            "The lab is complete. Proceed to Dr. Almeida's Flux Diagnostics Lab.",
        ]

        self.input()
        if not is_mission07_unlocked(self.missions_completed):
            self.menu_message(locked, buttons=False)
        elif '10' in self.missions_completed:
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

        image_path = get_resource_path('graphics/dialogues/nova.jpg')
        image = get_dialogue_portrait(image_path, (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_nome, 'Dr. Nova')
        self.screen.blit(name, (55, 677))

        for line, msg in enumerate(message):
            msg = prepare_dialogue_text(msg, self.player.player_name)
            surf = get_dialogue_text_surface(self.font, msg)
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                if target_mission == '10':
                    self.pending = Mission10_info(self.toggle_menu, self.player).update
                elif target_mission == '09':
                    self.pending = Mission09_info(self.toggle_menu, self.player).update
                elif target_mission == '08':
                    self.pending = Mission08_info(self.toggle_menu, self.player).update
                else:
                    self.pending = self.menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission07_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission07 = '07' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '07', self.missions_completed, mytheme)

        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)
        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 07',
            width=1280,
        )

        if not is_mission07_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 07 is locked. Complete Mission 06 with Dr. Carter before entering Dr. Nova's objective-comparison investigation.",
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
            theme=mytheme, title='Mission 07 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION07_METHOD}, keep the default medium and all genes unchanged, track {MISSION07_TARGET_FLUX}, and compare {MISSION07_BIOMASS_OBJECTIVE} with {MISSION07_TARGET_OBJECTIVE} as objectives.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 07 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: record one run that asks the model to maximise growth and another that asks it to maximise ethanol. Method, genes, medium and tracked fluxes must remain identical.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 07 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: an objective function is a modelling assumption that selects which feasible solution the algorithm seeks. It is not itself a biological intervention.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Mission 07 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            In the previous challenge, ethanol secretion was observed while the model still maximised biomass. Dr. Nova now wants to compare that question with direct {MISSION07_TARGET_PRODUCT} maximisation.

            Build a controlled objective comparison. Do not change the strain or the medium, and do not treat a positive product objective as proof of viable growth. Use the biomass, ethanol and oxygen fluxes returned by the same visible solution to interpret each run.

            Objective values from different reactions are different quantities. Compare the metabolic behaviour of the two solutions rather than subtracting their objective values.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 07: Objective Matters',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            f"""
            Compare two modelling questions while keeping the strain, environment and simulation method controlled.

            Target product: {MISSION07_TARGET_PRODUCT}

            Record both objective conditions and use the resulting growth and production evidence to explain what changed.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30,
        )
        menu.add.button('Mission 07 Briefing', briefing, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(30)

        report = load_mission07_objective_check()
        if report and report.get('mission_id') == '07' and report.get('check_version') == 3:
            menu.add.label(
                build_mission07_objective_comparison_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)

        if self.mission07:
            menu.add.button('Deliver Objective Comparison', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(30)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission07, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission07(self):
        if not is_mission07_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 06 first!', time=2500)
            return
        if '07' in self.missions_completed:
            self.mission07 = True
            animation_text_save('Mission 07 is already completed.', time=2500)
            return
        if '07' in self.missions_activated:
            self.mission07 = True
            animation_text_save('Mission 07 is already active.', time=2500)
            return

        clear_mission07_objective_check()
        self.mission07 = True
        if '07' not in self.missions_activated:
            self.missions_activated.insert(0, '07')
        animation_text_save('Mission 07 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        if not is_mission07_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 06 first!', time=2500)
            return
        if '07' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 07 before delivering results.', time=3000)
            return

        objective_data = load_mission07_objective_check()
        if (
            not objective_data
            or objective_data.get('mission_id') != '07'
            or objective_data.get('check_version') != 3
        ):
            self.failed.play()
            animation_text_save('Record both Mission 07 objective runs first!', time=2800)
            return

        if objective_data.get('evidence_ready'):
            self.success.play()
            if '07' not in self.missions_completed:
                self.missions_completed.insert(0, '07')
            animation_text_save('Congratulations! Mission 07 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        missing = []
        if not objective_data.get('reference_recorded'):
            missing.append('biomass-objective run')
        if not objective_data.get('target_recorded'):
            missing.append('ethanol-objective run')
        if missing:
            animation_text_save('Missing: ' + ', '.join(missing), time=3200)
        elif objective_data.get('current_issues'):
            animation_text_save(objective_data['current_issues'][0], time=3500)
        else:
            animation_text_save('Complete the controlled objective comparison first!', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
