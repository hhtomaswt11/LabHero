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
    MISSION40_CHECK_VERSION,
    MISSION40_METHOD,
    MISSION40_GROWTH_OBJECTIVE,
    MISSION40_REQUIRED_PRODUCTION_FLUXES,
    MISSION40_SWEEP_VALUES,
    MISSION40_MIN_ACETALDEHYDE_UPTAKE,
    MISSION40_MIN_MATCHED_GROWTH_FOLD,
    MISSION40_MIN_RESCUE_ETHANOL,
    build_mission40_final_certification_report_text,
    initialise_mission40_final_certification,
    is_mission40_unlocked,
    mission40_answer_matches,
)


class Mission40:
    """Final Golden Lab / yeast mission NPC (Mortis)."""

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
        self.menu40 = Mission40_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'The final certification is not open yet.',
            'Complete Morbus\'s bypass-rescue audit first.',
            'Return after Mission 39.',
        ]
        intro = [
            'Morbus found a rescue in one metabolic context.',
            'Now prove whether that rescue survives changing glucose capacity.',
            'Compare matched curves before you make the final call.',
        ]
        active = [
            'Mission 40 is active.',
            'Keep the genotype fixed and record both matched glucose curves.',
            'Only acetaldehyde availability may differ between the curves.',
        ]
        completed = [
            'Final certification complete.',
            'You proved that rescue strength depends on environmental context.',
            'You connected environment, GPR logic, background and pathway bypass.',
            'LabHero metabolic-model training is complete.',
        ]
        self.input()
        if '40' in self.missions_completed:
            self.menu_message(completed, buttons=False)
        elif '40' in self.missions_activated:
            self.menu_message(active, menu_to_open=self.menu40)
        elif is_mission40_unlocked(self.missions_completed):
            self.menu_message(intro, menu_to_open=self.menu40)
        else:
            self.menu_message(locked, buttons=False)
        if self.pending is not None:
            coro = self.pending
            self.pending = None
            await coro()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])
        image = get_dialogue_portrait(get_resource_path('graphics/dialogues/mortis.jpg'), (150, 150))
        self.screen.blit(image, (25, 520))
        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        self.screen.blit(get_dialogue_text_surface(self.font_name, 'Mortis'), (63, 677))
        for line, text in enumerate(message):
            text = prepare_dialogue_text(text, self.player.player_name)
            self.screen.blit(get_dialogue_text_surface(self.font, text), (200, 525 + line * 35))
        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu40).update
            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()
        pygame.display.flip()


class Mission40_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission40 = '40' in self.missions_activated
        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 40', width=1280,
        )
        if not is_mission40_unlocked(self.missions_completed):
            menu.add.label(
                'Mission 40 is locked. Complete Mission 39 first.',
                wordwrap=True, padding=(25,25,25,25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))
            await run_menu(menu, self.display_surface)
            return

        products = ', '.join(MISSION40_REQUIRED_PRODUCTION_FLUXES)
        bounds = ', '.join(f'{value:g}' for value in MISSION40_SWEEP_VALUES)
        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 40 Briefing', width=1280,
        )
        briefing.add.label(
            f"""Final matched rescue certification
- Model: Yeast iMM904
- Method: {MISSION40_METHOD}
- Objective: {MISSION40_GROWTH_OBJECTIVE}
- Genotype: PDC1 + PDC5 + PDC6 + FRD1 for both curves
- Production Flux: exactly {products}
- Bound Sweep: ON for both curves
- Sweep variable: EX_glc__D_e lower bound
- Preset/bounds: {bounds}

Record two matched curves in any order:
A. No-rescue curve: keep the base environment completely model-default.
B. Rescue curve: in Lower bounds to open enter only EX_acald_e. Leave every other environmental change empty.

The glucose sweep must be identical between the two curves. Compare acetaldehyde uptake, matched growth and ethanol secretion at the same glucose lower bound. The final answer is the complete set of tested bounds that satisfy all certification criteria.""",
            wordwrap=True, padding=(20,20,20,20), font_size=23,
        )
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        hint = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 40 Hint', width=1280,
        )
        hint.add.label(
            f'Compare rows horizontally between the two curves. A qualifying rescue row needs acetaldehyde uptake >= {MISSION40_MIN_ACETALDEHYDE_UPTAKE:.1f}, rescue growth >= {MISSION40_MIN_MATCHED_GROWTH_FOLD:.2f}x the matched no-rescue growth, and ethanol secretion >= {MISSION40_MIN_RESCUE_ETHANOL:.1f}. Not every glucose context needs to qualify.',
            wordwrap=True, padding=(20,20,20,20), font_size=25,
        )
        hint.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        menu.add.label(
            'Mission 40: Final Rescue Robustness Certification',
            align=pygame_menu.locals.ALIGN_CENTER, font_size=34,
        )
        menu.add.label(
            'Use matched glucose curves to decide where the acetaldehyde bypass remains a complete rescue.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=28,
        )
        menu.add.button('Mission Briefing', briefing, background_color=(255,215,0), font_color='black')
        menu.add.button('Optional Hint', hint, background_color=(230,230,180), font_color='black')

        report = load_mission40_final_certification()
        report_include_title = bool(
            self.mission40
            or '40' in self.missions_activated
            or '40' in self.missions_completed
        )
        menu.add.label(
            build_mission40_final_certification_report_text(
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

        if '40' in self.missions_completed:
            menu.add.label('Mission Completed — Final Certification Achieved', font_color=(40,120,40))
        elif self.mission40 or '40' in self.missions_activated:
            self.mission40 = True
            answer_input = menu.add.text_input(
                'Qualifying glucose LBs: ',
                default='',
                input_underline='_',
                maxchar=40,
                onreturn=self.deliver_results,
            )
            menu.add.button(
                'Deliver Final Interpretation',
                lambda: self.deliver_results(answer_input.get_value()),
                background_color=(50,100,100),
            )
            menu.add.label('Mission Activated', font_color=(150,150,150))
        else:
            menu.add.button('Activate Mission', self.activate_mission40, background_color=(50,100,100))
        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission40(self):
        if not is_mission40_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 39 first!', time=2500)
            return
        if '40' in self.missions_completed:
            return
        if '40' in self.missions_activated:
            self.mission40 = True
            return
        clear_mission40_final_certification()
        initialise_mission40_final_certification()
        self.mission40 = True
        self.missions_activated.insert(0, '40')
        save_file(self.player.get_save_data())
        animation_text_save('Mission 40 Activated')

    def deliver_results(self, answer):
        if not is_mission40_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 39 first!', time=2500)
            return
        if '40' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 40 first.', time=2500)
            return
        report = load_mission40_final_certification()
        if not report or report.get('mission_id') != '40' or report.get('check_version') != MISSION40_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Record current-format Mission 40 evidence first.', time=3000)
            return
        if not report.get('ready_to_deliver'):
            self.failed.play()
            animation_text_save('Complete both matched final curves first.', time=3000)
            return
        if not mission40_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recheck every tested bound against all three certification criteria.', time=3000)
            return
        self.success.play()
        if '40' not in self.missions_completed:
            self.missions_completed.insert(0, '40')
        save_file(self.player.get_save_data())
        animation_text_save('Mission 40 complete. LabHero certification achieved.', time=3500)

    async def update(self):
        self.timer.update()
        await self.setup()
