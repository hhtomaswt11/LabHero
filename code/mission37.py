import pygame
import pygame_menu

from answer_penalty import penalize_wrong_answer

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from utils import *
from hint_ui import MissionHintAccess
from simulation import (
    MISSION37_CHECK_VERSION,
    MISSION37_METHOD,
    MISSION37_GROWTH_OBJECTIVE,
    MISSION37_REQUIRED_PRODUCTION_FLUXES,
    MISSION37_GENOTYPE_LABELS,
    MISSION37_GENOTYPE_ORDER,
    build_mission37_fermentation_cut_set_report_text,
    initialise_mission37_fermentation_cut_set,
    is_mission37_unlocked,
    mission37_answer_matches,
)


class Mission37:
    """Second Golden Lab / yeast mission NPC (Voss)."""

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
        self.menu37 = Mission37_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'You are not ready for this cut-set audit yet.',
            'Finish Vale\'s fermentation-onset experiment first.',
            'Return after Mission 36.',
        ]
        intro = [
            'Vale showed you when fermentation appears.',
            'Now test how much genetic redundancy protects that phenotype.',
            'Use the yeast simulator to map the PDC cut set from visible flux evidence.',
        ]
        active = [
            'Mission 37 is active.',
            'Keep the medium fixed and build the requested PDC genotype series.',
            'Compare growth, ethanol, succinate and the GPR-disabled reactions.',
        ]
        completed = [
            'Good work.',
            'You separated gene count from reaction-level failure.',
            'The yeast programme can now move beyond a single fermentation route.',
        ]
        self.input()
        if '37' in self.missions_completed:
            self.menu_message(completed, buttons=False)
        elif '37' in self.missions_activated:
            self.menu_message(active, menu_to_open=self.menu37)
        elif self.player.is_mission_unlocked('37'):
            self.menu_message(intro, menu_to_open=self.menu37)
        else:
            self.menu_message(locked, buttons=False)
        if self.pending is not None:
            coro = self.pending
            self.pending = None
            await coro()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])
        image = get_dialogue_portrait(get_resource_path('graphics/dialogues/voss.jpg'), (150, 150))
        self.screen.blit(image, (25, 520))
        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        self.screen.blit(get_dialogue_text_surface(self.font_name, 'Voss'), (72, 677))
        for line, text in enumerate(message):
            text = prepare_dialogue_text(text, self.player.player_name)
            self.screen.blit(get_dialogue_text_surface(self.font, text), (200, 525 + line * 35))
        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu37).update
            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()
        pygame.display.flip()


class Mission37_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission37 = '37' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '37', self.missions_completed, mytheme)
        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 37', width=1280,
        overflow=(False, True),
        )
        if not self.player.is_mission_unlocked('37'):
            menu.add.label(
                'Mission 37 is locked. Complete Mission 36 first.',
                wordwrap=True, padding=(25,25,25,25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))
            await run_menu(menu, self.display_surface)
            return

        products = ', '.join(MISSION37_REQUIRED_PRODUCTION_FLUXES)
        genotype_lines = '\n'.join(
            f'- {MISSION37_GENOTYPE_LABELS[key]}' for key in MISSION37_GENOTYPE_ORDER
        )
        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 37 Briefing', width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""Controlled yeast cut-set screen
- Method: {MISSION37_METHOD}
- Objective: {MISSION37_GROWTH_OBJECTIVE}
- Environment: completely model-default
- Production Flux: exactly {products}
- Bound Sweep: not used; leave it off for this mission

Record these visible genotypes in any order:
{genotype_lines}

For every run, inspect growth, ethanol, succinate and the GPR-disabled reactions. Determine the smallest tested knockout set that simultaneously disables both pyruvate-decarboxylase target reactions, strongly suppresses ethanol relative to WT and still keeps the required fraction of WT growth.""",
            wordwrap=True, padding=(20,20,20,20), font_size=23,
        )
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 37 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            'Technical hint:\n\nAmong the tested genotypes that disable both target PDC reactions, keep only those retaining at least 50% of WT growth while leaving ethanol at no more than 1% of the WT level. Your answer is the smallest tested knockout set that satisfies all three conditions.',
            wordwrap=True, padding=(20,20,20,20), font_size=25,
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 37 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint:\n\nUse WT as the reference. For each tested genotype, first check whether both target pyruvate-decarboxylase reactions are disabled by the GPR logic. Only then compare its growth retention and ethanol retention with WT; a smaller gene set is useful only if it produces the required reaction-level failure.',
            wordwrap=True, padding=(20,20,20,20), font_size=26,
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255,215,0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 37 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint:\n\nDo not equate the number of knocked-out genes with the number of disabled reactions. Compare the GPR-disabled reaction list first, then use WT-normalised growth and ethanol retention to interpret the phenotype.',
            wordwrap=True, padding=(20,20,20,20), font_size=26,
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255,215,0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        menu.add.label(
            'Mission 37: Fermentation Redundancy Cut Set',
            align=pygame_menu.locals.ALIGN_CENTER, font_size=34,
        )
        menu.add.label(
            'Move from an environmental fermentation transition to a genetic robustness audit.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=28,
        )
        menu.add.button('Mission Briefing', briefing, background_color=(255,215,0), font_color='black')
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, background_color=(230,230,180), font_color='black')

        report = load_mission37_fermentation_cut_set()
        report_include_title = bool(
            self.mission37
            or '37' in self.missions_activated
            or '37' in self.missions_completed
        )
        menu.add.label(
            build_mission37_fermentation_cut_set_report_text(
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

        if '37' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40,120,40))
        elif self.mission37 or '37' in self.missions_activated:
            self.mission37 = True
            answer_input = menu.add.text_input(
                'Smallest tested PDC cut set: ',
                default='',
                input_underline='_',
                maxchar=48,
                onreturn=self.deliver_results,
            )
            menu.add.button(
                'Deliver Interpretation',
                lambda: self.deliver_results(answer_input.get_value()),
                background_color=(50,100,100),
            )
            menu.add.label('Mission Activated', font_color=(150,150,150))
        else:
            menu.add.button('Activate Mission', self.activate_mission37, background_color=(50,100,100))
        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission37(self):
        if not self.player.is_mission_unlocked('37'):
            self.failed.play()
            animation_text_save('Complete Mission 36 first!', time=2500)
            return
        if '37' in self.missions_completed:
            return
        if '37' in self.missions_activated:
            self.mission37 = True
            return
        clear_mission37_fermentation_cut_set()
        initialise_mission37_fermentation_cut_set()
        self.mission37 = True
        self.missions_activated.insert(0, '37')
        save_file(self.player.get_save_data())
        animation_text_save('Mission 37 Activated')

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('37'):
            self.failed.play()
            animation_text_save('Complete Mission 36 first!', time=2500)
            return
        if '37' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 37 first.', time=2500)
            return
        report = load_mission37_fermentation_cut_set()
        if not report or report.get('mission_id') != '37' or report.get('check_version') != MISSION37_CHECK_VERSION:
            self.failed.play()
            animation_text_save('Record current-format Mission 37 evidence first.', time=3000)
            return
        if not report.get('ready_to_deliver'):
            self.failed.play()
            animation_text_save('Complete the controlled PDC genotype screen first.', time=3000)
            return
        if not mission37_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recheck the smallest tested cut set that satisfies every visible criterion.', time=3000)
            penalize_wrong_answer(self.player, '37')
            return
        self.success.play()
        if '37' not in self.missions_completed:
            self.missions_completed.insert(0, '37')
        save_file(self.player.get_save_data())
        animation_text_save('Congratulations! Mission 37 completed!', time=3200)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
