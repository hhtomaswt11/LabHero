import pygame
import pygame_menu

from settings import *
from save_load import *
from timers import Timer
from options_values import mytheme
from functions import animation_text_save
from async_menu import run_menu
from utils import *
from simulation import (
    MISSION28_CHECK_VERSION,
    MISSION28_METHOD,
    MISSION28_GROWTH_OBJECTIVE,
    MISSION28_PRIMARY_GENE,
    MISSION28_PRIMARY_GENE_NAME,
    MISSION28_PRIMARY_REACTION,
    MISSION28_RESCUE_SUPPLEMENT,
    MISSION28_RESCUE_SUPPLEMENT_NAME,
    MISSION28_SECONDARY_GENES,
    MISSION28_SECONDARY_GENE_NAMES,
    MISSION28_SECONDARY_REACTIONS,
    build_mission28_dependency_report_text,
    initialise_mission28_dependency_screen,
    is_mission28_unlocked,
    mission28_answer_matches,
)


class Mission28_info:
    """Mission 28 — Bypass Dependency Mapping, Dr. Ribeiro."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission28 = '28' in self.missions_activated

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
            title='Mission 28',
            width=1280,
        )

        if not is_mission28_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 28 is locked. Complete Mission 27 before beginning Dr. Ribeiro's dependency-mapping experiment.",
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        candidate_lines = '\n'.join(
            f'- {gene_id} / {MISSION28_SECONDARY_GENE_NAMES[gene_id]}: disables {MISSION28_SECONDARY_REACTIONS[gene_id]}'
            for gene_id in MISSION28_SECONDARY_GENES
        )

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 28 Hint 3', width=1280,
        )
        hint3.add.label(
            f"Technical hint: use {MISSION28_METHOD} with objective {MISSION28_GROWTH_OBJECTIVE}. Keep {MISSION28_PRIMARY_GENE} / {MISSION28_PRIMARY_GENE_NAME} knocked out and open only the {MISSION28_RESCUE_SUPPLEMENT} lower bound. Record the rescue reference with no second knockout, then add exactly one highlighted secondary gene per trial. Leave glucose, oxygen and every unrelated bound at model default. No Production Flux selection is required.",
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 28 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: a dependency should affect both the rescue phenotype and measured 2-oxoglutarate uptake. Compare every double knockout with the same single-knockout rescue reference.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint', hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 28 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: external availability is not the same as intracellular access. Look for the secondary knockout that removes supplement uptake and collapses the rescue while citrate synthase remains disabled.',
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
            title='Mission 28 Briefing',
            width=1280,
        )
        briefing.add.label(
            f"""
            Dr. Ribeiro wants a mechanism-level dependency map of the Mission 27 rescue.

            Fixed rescue background:
            - Method: {MISSION28_METHOD}
            - Objective: {MISSION28_GROWTH_OBJECTIVE}
            - Keep {MISSION28_PRIMARY_GENE} / {MISSION28_PRIMARY_GENE_NAME} knocked out
            - Keep {MISSION28_RESCUE_SUPPLEMENT} / {MISSION28_RESCUE_SUPPLEMENT_NAME} as the only opened supplement lower bound
            - {MISSION28_PRIMARY_REACTION} must remain disabled through the GPR

            First establish or reuse the single-knockout rescue reference. Then add exactly one secondary candidate knockout per run:
            {candidate_lines}

            Keep glucose, oxygen and every unrelated bound at model default. The report accumulates one reference and five visible double-knockout trials in any order.

            Compare rescue retention, measured 2-oxoglutarate uptake and GPR-disabled reactions. Identify the secondary knockout that removes the function required for the rescue. The conclusion is conditional on this model, objective, medium, bounds and candidate set.
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
            'Mission 28: Bypass Dependency Mapping',
            wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Map the network function required for the 2-oxoglutarate rescue while keeping the original gltA lesion fixed.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=28,
        )
        menu.add.button('Mission 28 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints', hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission28_dependency_check()
        report_label_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 22,
        }
        if report:
            report_label_options['background_color'] = 'white'
        menu.add.label(
            build_mission28_dependency_report_text(report),
            **report_label_options,
        )
        menu.add.vertical_margin(20)

        if '28' in self.missions_completed:
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
        elif self.mission28 or '28' in self.missions_activated:
            self.mission28 = True
            menu.add.label(
                'Question: Which secondary gene knockout abolished the rescue by preventing 2-oxoglutarate uptake while citrate synthase remained disabled?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Dependency gene: ',
                default='',
                input_underline='_',
                maxchar=100,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission28, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission28(self):
        if not is_mission28_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 27 before starting Mission 28.', time=3000)
            return
        if '28' in self.missions_completed:
            return
        if '28' in self.missions_activated:
            self.mission28 = True
            return

        clear_bound_sweep()
        clear_mission28_dependency_check()
        initialise_mission28_dependency_screen(load_mission27_rescue_check() or {})
        self.mission28 = True
        self.missions_activated.insert(0, '28')
        animation_text_save('Mission 28 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not is_mission28_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 27 first!', time=2500)
            return
        if '28' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 28 before delivering a conclusion.', time=2800)
            return

        report = load_mission28_dependency_check()
        if (
            not report
            or report.get('mission_id') != '28'
            or report.get('check_version') != MISSION28_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 28 dependency screen first.', time=3000)
            return
        if not report.get('evidence_ready') or not report.get('unique_transport_dependency_supported'):
            self.failed.play()
            animation_text_save('Complete the rescue reference and all five controlled secondary-knockout trials before answering.', time=3400)
            return
        if not mission28_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('Recompare rescue retention, 2-oxoglutarate uptake and GPR-disabled reactions.', time=3300)
            return

        self.success.play()
        if '28' not in self.missions_completed:
            self.missions_completed.insert(0, '28')
        animation_text_save('Congratulations! Mission 28 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
