import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from async_menu import run_menu
from simulation import (
    MISSION08_METHOD,
    MISSION08_TARGET_PRODUCT,
    MISSION08_TARGET_OBJECTIVE,
    MISSION08_TARGET_FLUX,
    MISSION08_OXYGEN_REACTION,
    is_mission08_unlocked,
    build_mission08_constraint_comparison_report_text,
)


class Mission08_info:
    """Mission 08 — Constraint Impact on the Optimal Solution."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)
        self.mission08 = '08' in self.missions_activated

        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)
        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720, center_content=False, onclose=self.toggle_menu,
            theme=mytheme, title='Mission 08', width=1280,
        )

        if not is_mission08_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 08 is locked. Complete the controlled objective comparison in Mission 07 before studying environmental constraints.',
                wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25), background_color='white', font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 08 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: use {MISSION08_METHOD}, maximise {MISSION08_TARGET_OBJECTIVE}, keep all genes active, track {MISSION08_TARGET_FLUX}, and compare the default medium with a run in which only the lower bound of {MISSION08_OXYGEN_REACTION} is closed.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 08 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: observe oxygen uptake before imposing the constraint. Keep the objective, genes, method and all other environmental bounds identical between the two runs.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 08 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: a new constraint changes the optimum only if it removes or limits something that the previous optimum was able to use.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint', hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 08 Briefing', width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Nova wants to test a modelling hypothesis: does making oxygen unavailable necessarily increase the maximum predicted secretion of {MISSION08_TARGET_PRODUCT}?

            Construct a controlled before-and-after comparison. Keep the strain, objective, method and remaining medium identical, and use the fluxes returned by each visible solution to decide whether the added constraint actually changed the optimum.

            This mission concerns a theoretical direct-product optimum. A positive product flux must not be interpreted as proof of viable growth.
            """,
            max_char=-1, wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints', hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label('Mission 08: Constraint Impact on the Optimal Solution', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            f"""
            Test whether one environmental restriction changes the direct {MISSION08_TARGET_PRODUCT} optimum.

            Record both controlled conditions and determine from the resulting production, growth and oxygen evidence whether the new restriction changes the optimum.
            """,
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=30,
        )
        menu.add.button('Mission 08 Briefing', briefing, font_color='black', background_color=(255, 215, 0, 255))
        menu.add.vertical_margin(30)

        report = load_mission08_constraint_check()
        if report and report.get('mission_id') == '08' and report.get('check_version') == 4:
            menu.add.label(
                build_mission08_constraint_comparison_report_text(report),
                wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20), background_color='white', font_size=22,
            )
            menu.add.vertical_margin(20)

        if self.mission08:
            menu.add.button('Deliver Constraint Comparison', action=self.deliver_results, background_color=(50, 100, 100))
            menu.add.vertical_margin(30)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission08, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission08(self):
        if not is_mission08_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 07 first!', time=2500)
            return
        if '08' in self.missions_completed:
            self.mission08 = True
            animation_text_save('Mission 08 is already completed.', time=2500)
            return
        if '08' in self.missions_activated:
            self.mission08 = True
            animation_text_save('Mission 08 is already active.', time=2500)
            return

        clear_mission08_constraint_check()
        self.mission08 = True
        if '08' not in self.missions_activated:
            self.missions_activated.insert(0, '08')
        animation_text_save('Mission 08 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self):
        if not is_mission08_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 07 first!', time=2500)
            return
        if '08' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 08 before delivering results.', time=3000)
            return

        report = load_mission08_constraint_check()
        if (
            not report
            or report.get('mission_id') != '08'
            or report.get('check_version') != 4
        ):
            self.failed.play()
            animation_text_save('Record both Mission 08 constraint runs first!', time=2800)
            return

        if report.get('evidence_ready') and report.get('optimum_unchanged'):
            self.success.play()
            if '08' not in self.missions_completed:
                self.missions_completed.insert(0, '08')
            animation_text_save('Congratulations! Mission 08 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        missing = []
        if not report.get('default_recorded'):
            missing.append('default-medium run')
        if not report.get('constrained_recorded'):
            missing.append('oxygen-constrained run')
        if missing:
            animation_text_save('Missing: ' + ', '.join(missing), time=3200)
        elif report.get('current_issues'):
            animation_text_save(report['current_issues'][0], time=3500)
        else:
            animation_text_save('Complete the controlled constraint comparison first!', time=3000)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
