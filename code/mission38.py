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
    MISSION38_CHECK_VERSION,
    MISSION38_METHOD,
    MISSION38_GROWTH_OBJECTIVE,
    MISSION38_REQUIRED_PRODUCTION_FLUXES,
    MISSION38_CONDITION_LABELS,
    MISSION38_CONDITION_ORDER,
    MISSION38_MIN_SINGLE_GROWTH_RETENTION,
    MISSION38_MAX_COMBINED_GROWTH_RETENTION,
    MISSION38_MAX_COMBINED_SUCCINATE_RETENTION,
    MISSION38_MIN_PYRUVATE_SECRETION,
    build_mission38_background_dependency_report_text,
    initialise_mission38_background_dependency,
    is_mission38_unlocked,
    mission38_answer_matches,
)


class Mission38:
    """Third Golden Lab / yeast mission NPC (Umbra)."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.screen = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.font_name = pygame.font.Font(font_path, 24)
        self.timer = Timer(200)
        self.menu38 = Mission38_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'This dependency audit is not ready for you yet.',
            'Finish Voss\'s PDC cut-set experiment first.',
            'Return after Mission 37.',
        ]
        intro = [
            'Voss exposed a compensatory state after the PDC cut set.',
            'Now ask whether apparently harmless genes remain harmless in that new background.',
            'Build a matched matrix to separate general effects from background-specific effects.',
        ]
        active = [
            'Mission 38 is active.',
            'Keep the medium fixed and compare FRD1 and MAE1 in both genetic backgrounds.',
            'Use growth, succinate, pyruvate and the GPR-disabled reactions as visible evidence.',
        ]
        completed = [
            'Good work.',
            'You showed that gene effects depend on genetic background.',
            'A compensatory route can become a vulnerability',
            'only after another pathway has already been removed.',
        ]
        self.input()
        if '38' in self.missions_completed:
            self.menu_message(completed, buttons=False)
        elif '38' in self.missions_activated:
            self.menu_message(active, menu_to_open=self.menu38)
        elif is_mission38_unlocked(self.missions_completed):
            self.menu_message(intro, menu_to_open=self.menu38)
        else:
            self.menu_message(locked, buttons=False)
        if self.pending is not None:
            coro = self.pending
            self.pending = None
            await coro()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])
        image = pygame.image.load(get_resource_path('graphics/dialogues/umbra.jpg')).convert()
        if image.get_size() != (150, 150):
            image = pygame.transform.smoothscale(image, (150, 150))
        self.screen.blit(image, (25, 520))
        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        self.screen.blit(self.font_name.render('Umbra', True, 'black'), (66, 677))
        for line, text in enumerate(message):
            text = prepare_dialogue_text(text, self.player.player_name)
            self.screen.blit(self.font.render(text, True, 'black'), (200, 525 + line * 35))
        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu38).update
            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()
        pygame.display.flip()


class Mission38_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission38 = '38' in self.missions_activated
        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 38', width=1280,
        )
        if not is_mission38_unlocked(self.missions_completed):
            menu.add.label(
                'Mission 38 is locked. Complete Mission 37 first.',
                wordwrap=True, padding=(25,25,25,25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))
            await run_menu(menu, self.display_surface)
            return

        products = ', '.join(MISSION38_REQUIRED_PRODUCTION_FLUXES)
        condition_lines = '\n'.join(
            f'- {MISSION38_CONDITION_LABELS[key]}' for key in MISSION38_CONDITION_ORDER
        )
        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 38 Briefing', width=1280,
        )
        briefing.add.label(
            f"""Controlled yeast dependency matrix
- Method: {MISSION38_METHOD}
- Objective: {MISSION38_GROWTH_OBJECTIVE}
- Environment: completely model-default
- Production Flux: exactly {products}
- Bound Sweep: not used; leave it off for this mission

Record these visible conditions in any order:
{condition_lines}

Use WT to judge whether each candidate is generally growth-limiting. Then use the PDC1+PDC5+PDC6 run as the matched background reference and compare what FRD1 or MAE1 does to growth, succinate and pyruvate in that background.""",
            wordwrap=True, padding=(20,20,20,20), font_size=23,
        )
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        hint = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 38 Hint', width=1280,
        )
        hint.add.label(
            'Compare the same candidate in two backgrounds. A useful background-specific vulnerability should be nearly neutral by itself, but should cause a much larger change after the PDC cut set is already present. Do not judge from a single genotype in isolation.',
            wordwrap=True, padding=(20,20,20,20), font_size=26,
        )
        hint.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        menu.add.label(
            'Mission 38: Background-Dependent Compensation Audit',
            align=pygame_menu.locals.ALIGN_CENTER, font_size=34,
        )
        menu.add.label(
            'Test whether a gene that is quiet in one background becomes a vulnerability in another.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=28,
        )
        menu.add.button('Mission Briefing', briefing, background_color=(255,215,0), font_color='black')
        menu.add.button('Optional Hint', hint, background_color=(230,230,180), font_color='black')

        report = load_mission38_background_dependency()
        report_include_title = bool(
            self.mission38
            or '38' in self.missions_activated
            or '38' in self.missions_completed
        )
        menu.add.label(
            build_mission38_background_dependency_report_text(
                report,
                include_title=report_include_title,
            ),
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20,20,20,20),
            background_color='white' if report else None,
            font_size=22,
        )
        menu.add.vertical_margin(20)

        if '38' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40,120,40))
        elif self.mission38 or '38' in self.missions_activated:
            self.mission38 = True
            answer_input = menu.add.text_input(
                'Background-specific candidate gene: ',
                default='',
                input_underline='_',
                maxchar=24,
                onreturn=self.deliver_results,
            )
            menu.add.button(
                'Deliver Interpretation',
                lambda: self.deliver_results(answer_input.get_value()),
                background_color=(50,100,100),
            )
            menu.add.label('Mission Activated', font_color=(150,150,150))
        else:
            menu.add.button('Activate Mission', self.activate_mission38, background_color=(50,100,100))
        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission38(self):
        if not is_mission38_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 37 first!', time=2500)
            return
        if '38' in self.missions_completed:
            return
        if '38' in self.missions_activated:
            self.mission38 = True
            return
        clear_mission38_background_dependency()
        initialise_mission38_background_dependency()
        self.mission38 = True
        self.missions_activated.insert(0, '38')
        save_file(self.player.get_save_data())
        animation_text_save('Mission 38 Activated')

    def deliver_results(self, answer):
        if not is_mission38_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 37 first!', time=2500)
            return
        if '38' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 38 first.', time=2500)
            return
        report = load_mission38_background_dependency()
        if not report or report.get('mission_id') != '38' or report.get('check_version') != MISSION38_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Record current-format Mission 38 evidence first.', time=3000)
            return
        if not report.get('ready_to_deliver'):
            self.failed.play()
            animation_text_save('Complete the controlled dependency matrix first.', time=3000)
            return
        if not mission38_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recheck which candidate changes specifically in the PDC-cut-set background.', time=3000)
            return
        self.success.play()
        if '38' not in self.missions_completed:
            self.missions_completed.insert(0, '38')
        save_file(self.player.get_save_data())
        animation_text_save('Congratulations! Mission 38 completed!', time=3200)

    async def update(self):
        self.timer.update()
        await self.setup()
