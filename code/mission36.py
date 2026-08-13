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
    MISSION36_CHECK_VERSION,
    MISSION36_METHOD,
    MISSION36_GROWTH_OBJECTIVE,
    MISSION36_REQUIRED_PRODUCTION_FLUXES,
    MISSION36_SWEEP_VALUES,
    build_mission36_fermentation_report_text,
    initialise_mission36_fermentation_onset,
    is_mission36_unlocked,
    mission36_answer_matches,
)


class Mission36:
    """First Golden Lab / yeast mission NPC (Vale)."""

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
        self.menu36 = Mission36_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked = [
            'The yeast programme is still locked.',
            'Complete the E. coli certification first.',
            'Return after Mission 35.',
        ]
        intro = [
            'Welcome to the yeast programme.',
            'Keep oxygen fixed and increase glucose availability.',
            'Find when fermentation appears as the oxygen cap becomes binding.',
        ]
        active = [
            'Mission 36 is active.',
            'Build the default pFBA reference, then run the glucose threshold sweep.',
            'Compare realised O2 uptake with ethanol secretion across the tested bounds.',
        ]
        completed = [
            'Excellent.',
            'You identified the transition supported by the yeast flux evidence.',
            'The next yeast experiment will build on this constraint interaction.',
        ]
        self.input()
        if '36' in self.missions_completed:
            self.menu_message(completed, buttons=False)
        elif '36' in self.missions_activated:
            self.menu_message(active, menu_to_open=self.menu36)
        elif is_mission36_unlocked(self.missions_completed):
            self.menu_message(intro, menu_to_open=self.menu36)
        else:
            self.menu_message(locked, buttons=False)
        if self.pending is not None:
            coro = self.pending
            self.pending = None
            await coro()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])
        image = pygame.image.load(get_resource_path('graphics/dialogues/vale.jpg')).convert()
        if image.get_size() != (150, 150):
            image = pygame.transform.smoothscale(image, (150, 150))
        self.screen.blit(image, (25, 520))
        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        self.screen.blit(self.font_name.render('Vale', True, 'black'), (70, 677))
        for line, text in enumerate(message):
            text = prepare_dialogue_text(text, self.player.player_name)
            self.screen.blit(self.font.render(text, True, 'black'), (200, 525 + line * 35))
        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu36).update
            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()
        pygame.display.flip()


class Mission36_info:
    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission36 = '36' in self.missions_activated
        self.success = pygame.mixer.Sound(get_resource_path('audio/success_3.ogg'))
        self.success.set_volume(1.2)
        self.failed = pygame.mixer.Sound(get_resource_path('audio/failed.ogg'))
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(height=720, center_content=False, onclose=self.toggle_menu, theme=mytheme, title='Mission 36', width=1280)
        if not is_mission36_unlocked(self.missions_completed):
            menu.add.label('Mission 36 is locked. Complete Mission 35 first.', wordwrap=True, padding=(25,25,25,25), background_color='white', font_size=30)
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))
            await run_menu(menu, self.display_surface)
            return

        values = ', '.join(f'{v:g}' for v in MISSION36_SWEEP_VALUES)
        products = ', '.join(MISSION36_REQUIRED_PRODUCTION_FLUXES)
        briefing = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 36 Briefing', width=1280)
        briefing.add.label(
            f"""A — Default yeast reference\n- Method: {MISSION36_METHOD}\n- Objective: {MISSION36_GROWTH_OBJECTIVE}\n- Genotype: wild type\n- Environment: completely model-default\n- Production Flux: exactly {products}\n\nB — Glucose availability curve\n- Keep the same method, objective, genotype and base environment\n- Bound Sweep: EX_glc__D_e lower bound\n- Dedicated yeast preset: {values}\n\nUse the visible rows to determine when the fixed oxygen capacity first becomes binding at the same tested point where ethanol secretion is positive.""",
            wordwrap=True, padding=(20,20,20,20), font_size=24,
        )
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        hint = pygame_menu.Menu(height=720, center_content=False, onclose=pygame_menu.events.BACK, theme=mytheme, title='Mission 36 Hint', width=1280)
        hint.add.label(
            'A configured bound is not automatically active. Compare the realised O2 uptake in each row with the fixed O2 uptake capacity, then inspect when ethanol changes from zero to positive.',
            wordwrap=True, padding=(20,20,20,20), font_size=26,
        )
        hint.add.button('Back', pygame_menu.events.BACK, background_color=(70,70,70))

        menu.add.label('Mission 36: Oxygen-Capped Fermentation Onset', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label('Transfer your constraint-based reasoning to the larger yeast model.', wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=28)
        menu.add.button('Mission Briefing', briefing, background_color=(255,215,0), font_color='black')
        menu.add.button('Optional Hint', hint, background_color=(230,230,180), font_color='black')
        report = load_mission36_fermentation_onset()
        # Keep the landing/activation screen compact because the mission title is
        # already displayed prominently above.  Once Mission 36 is active, the
        # block below is the persistent mission report shown when the player
        # returns to Vale; match the historical Mission 29-35 report convention
        # by including the mission number/name at the start of that report.
        report_include_title = bool(
            self.mission36
            or '36' in self.missions_activated
            or '36' in self.missions_completed
        )
        menu.add.label(
            build_mission36_fermentation_report_text(
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

        if '36' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40,120,40))
        elif self.mission36 or '36' in self.missions_activated:
            self.mission36 = True
            answer_input = menu.add.text_input(
                'First tested glucose lower bound: ',
                default='',
                input_underline='_',
                maxchar=24,
                onreturn=self.deliver_results,
            )
            menu.add.button('Deliver Interpretation', lambda: self.deliver_results(answer_input.get_value()), background_color=(50,100,100))
            menu.add.label('Mission Activated', font_color=(150,150,150))
        else:
            menu.add.button('Activate Mission', self.activate_mission36, background_color=(50,100,100))
        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission36(self):
        if not is_mission36_unlocked(self.missions_completed):
            self.failed.play(); animation_text_save('Complete Mission 35 first!', time=2500); return
        if '36' in self.missions_completed:
            return
        if '36' in self.missions_activated:
            self.mission36 = True; return
        clear_mission36_fermentation_onset()
        initialise_mission36_fermentation_onset()
        self.mission36 = True
        self.missions_activated.insert(0, '36')
        save_file(self.player.get_save_data())
        animation_text_save('Mission 36 Activated')

    def deliver_results(self, answer):
        if not is_mission36_unlocked(self.missions_completed):
            self.failed.play(); animation_text_save('Complete Mission 35 first!', time=2500); return
        if '36' not in self.missions_activated:
            self.failed.play(); animation_text_save('Activate Mission 36 first.', time=2500); return
        report = load_mission36_fermentation_onset()
        if not report or report.get('mission_id') != '36' or report.get('check_version') != MISSION36_CHECK_VERSION:
            self.failed.play(); animation_text_save('Record current-format Mission 36 evidence first.', time=3000); return
        if not report.get('ready_to_deliver'):
            self.failed.play(); animation_text_save('Complete the reference and glucose curve first.', time=3000); return
        if not mission36_answer_matches(answer, report):
            self.failed.play(); animation_text_save('Recheck the first tested row where both conditions are satisfied.', time=3000); return
        self.success.play()
        if '36' not in self.missions_completed:
            self.missions_completed.insert(0, '36')
        save_file(self.player.get_save_data())
        animation_text_save('Congratulations! Mission 36 completed!', time=3200)

    def input(self):
        keys = pygame.key.get_pressed(); self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input(); await self.setup()
