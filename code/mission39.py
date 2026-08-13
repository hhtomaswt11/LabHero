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
    MISSION39_CHECK_VERSION,
    MISSION39_METHOD,
    MISSION39_GROWTH_OBJECTIVE,
    MISSION39_REQUIRED_PRODUCTION_FLUXES,
    MISSION39_CONDITION_LABELS,
    MISSION39_CONDITION_ORDER,
    MISSION39_MIN_RESCUE_GROWTH_FOLD,
    MISSION39_MIN_RESCUE_ETHANOL,
    MISSION39_MIN_SUPPLEMENT_UPTAKE,
    build_mission39_bypass_rescue_report_text,
    initialise_mission39_bypass_rescue,
    is_mission39_unlocked,
    mission39_answer_matches,
)


class Mission39:
    """Fourth Golden Lab / yeast mission NPC (Morbus)."""

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
        self.menu39 = Mission39_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'This bypass audit is not ready yet.',
            'Finish Umbra\'s background-dependency experiment first.',
            'Return after Mission 38.',
        ]
        intro = [
            'Umbra exposed a fragile PDC-plus-FRD1 background.',
            'Now test whether pathway-related supplements can bypass that state.',
            'Compare availability with actual uptake and rescue.',
        ]
        active = [
            'Mission 39 is active.',
            'Keep the genotype fixed and open only one tested uptake at a time.',
            'Use growth, uptake and ethanol recovery as visible evidence.',
        ]
        completed = [
            'Good work.',
            'You found a bypass that rescues this constrained state.',
            'But one successful rescue is not proof of robustness.',
            'Mortis will test whether it survives a changing environment.',
        ]
        self.input()
        if '39' in self.missions_completed:
            self.menu_message(completed, buttons=False)
        elif '39' in self.missions_activated:
            self.menu_message(active, menu_to_open=self.menu39)
        elif is_mission39_unlocked(self.missions_completed):
            self.menu_message(intro, menu_to_open=self.menu39)
        else:
            self.menu_message(locked, buttons=False)
        if self.pending is not None:
            coro = self.pending
            self.pending = None
            await coro()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])
        image = pygame.image.load(get_resource_path('graphics/dialogues/morbus.jpg')).convert()
        if image.get_size() != (150, 150):
            image = pygame.transform.smoothscale(image, (150, 150))
        self.screen.blit(image, (25, 520))
        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        self.screen.blit(self.font_name.render('Morbus', True, 'black'), (63, 677))
        for line, text in enumerate(message):
            text = prepare_dialogue_text(text, self.player.player_name)
            self.screen.blit(self.font.render(text, True, 'black'), (200, 525 + line * 35))
        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu39).update
            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()
        pygame.display.flip()


class Mission39_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission39 = '39' in self.missions_activated
        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 39', width=1280,
        )
        if not is_mission39_unlocked(self.missions_completed):
            menu.add.label(
                'Mission 39 is locked. Complete Mission 38 first.',
                wordwrap=True, padding=(25,25,25,25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))
            await run_menu(menu, self.display_surface)
            return

        products = ', '.join(MISSION39_REQUIRED_PRODUCTION_FLUXES)
        condition_lines = '\n'.join(
            f'- {MISSION39_CONDITION_LABELS[key]}' for key in MISSION39_CONDITION_ORDER
        )
        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 39 Briefing', width=1280,
        )
        briefing.add.label(
            f"""Controlled yeast bypass screen
- Method: {MISSION39_METHOD}
- Objective: {MISSION39_GROWTH_OBJECTIVE}
- Genotype: PDC1 + PDC5 + PDC6 + FRD1 for every run
- Production Flux: exactly {products}
- Bound Sweep: not used; leave it off for this mission

Record these four environments in any order:
{condition_lines}

For the three supplement runs, use Lower bounds to open and enter only the stated exchange ID. Keep every other environmental field empty. Compare the default-medium reference with the three one-at-a-time openings. Availability alone is not enough: inspect whether the supplement is actually taken up and whether growth and ethanol recover.""",
            wordwrap=True, padding=(20,20,20,20), font_size=23,
        )
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        hint = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 39 Hint', width=1280,
        )
        hint.add.label(
            'Think about pathway order. Pyruvate lies before the blocked decarboxylase step, acetaldehyde is its immediate product, and ethanol lies further downstream. A useful bypass should change the phenotype, not merely make an exchange available.',
            wordwrap=True, padding=(20,20,20,20), font_size=26,
        )
        hint.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        menu.add.label(
            'Mission 39: Pathway Bypass Rescue',
            align=pygame_menu.locals.ALIGN_CENTER, font_size=34,
        )
        menu.add.label(
            'Use controlled supplementation to test which pathway-level bypass can rescue the vulnerable background.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=28,
        )
        menu.add.button('Mission Briefing', briefing, background_color=(255,215,0), font_color='black')
        menu.add.button('Optional Hint', hint, background_color=(230,230,180), font_color='black')

        report = load_mission39_bypass_rescue()
        report_include_title = bool(
            self.mission39
            or '39' in self.missions_activated
            or '39' in self.missions_completed
        )
        menu.add.label(
            build_mission39_bypass_rescue_report_text(
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

        if '39' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40,120,40))
        elif self.mission39 or '39' in self.missions_activated:
            self.mission39 = True
            answer_input = menu.add.text_input(
                'Bypass supplement: ',
                default='',
                input_underline='_',
                maxchar=32,
                onreturn=self.deliver_results,
            )
            menu.add.button(
                'Deliver Interpretation',
                lambda: self.deliver_results(answer_input.get_value()),
                background_color=(50,100,100),
            )
            menu.add.label('Mission Activated', font_color=(150,150,150))
        else:
            menu.add.button('Activate Mission', self.activate_mission39, background_color=(50,100,100))
        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission39(self):
        if not is_mission39_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 38 first!', time=2500)
            return
        if '39' in self.missions_completed:
            return
        if '39' in self.missions_activated:
            self.mission39 = True
            return
        clear_mission39_bypass_rescue()
        initialise_mission39_bypass_rescue()
        self.mission39 = True
        self.missions_activated.insert(0, '39')
        save_file(self.player.get_save_data())
        animation_text_save('Mission 39 Activated')

    def deliver_results(self, answer):
        if not is_mission39_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 38 first!', time=2500)
            return
        if '39' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 39 first.', time=2500)
            return
        report = load_mission39_bypass_rescue()
        if not report or report.get('mission_id') != '39' or report.get('check_version') != MISSION39_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Record current-format Mission 39 evidence first.', time=3000)
            return
        if not report.get('ready_to_deliver'):
            self.failed.play()
            animation_text_save('Complete the controlled bypass screen first.', time=3000)
            return
        if not mission39_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recheck which tested opening gives a strong growth and ethanol rescue.', time=3000)
            return
        self.success.play()
        if '39' not in self.missions_completed:
            self.missions_completed.insert(0, '39')
        save_file(self.player.get_save_data())
        animation_text_save('Congratulations! Mission 39 completed!', time=3200)

    async def update(self):
        self.timer.update()
        await self.setup()
