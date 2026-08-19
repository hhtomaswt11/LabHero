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
from hint_ui import MissionHintAccess
from progression import mission35_reward_state
from simulation import (
    MISSION35_CHECK_VERSION,
    MISSION35_METHOD,
    MISSION35_GROWTH_OBJECTIVE,
    MISSION35_FORMATE_OBJECTIVE,
    MISSION35_DESIGN_LABELS,
    MISSION35_DESIGN_ORDER,
    MISSION35_REQUIRED_PRODUCTION_FLUXES,
    MISSION35_SWEEP_VALUES,
    MISSION35_SWEEP_PRESET,
    MISSION35_APPROVAL_MIN_FORMATE,
    MISSION35_APPROVAL_MIN_GROWTH_RETENTION,
    MISSION35_APPROVAL_MAX_DISABLED_REACTIONS,
    build_mission35_final_certification_report_text,
    initialise_mission35_final_certification,
    is_mission35_unlocked,
    mission35_answer_checks,
    mission35_answers_match,
)


class Mission35:
    """Final E. coli certification NPC (Dr. Richter)."""

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
        self.menu35 = Mission35_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked_dialogue = [
            'Your final E. coli qualification is still locked.',
            "Complete Dr. Chen's programme first.",
            'Return when all thirty-four missions are complete.',
        ]
        intro_dialogue = [
            'Your final E. coli certification begins now.',
            'Approve one design, test oxygen robustness and audit its objective.',
            'Complete the full dossier before entering the Golden Lab.',
        ]
        active_dialogue = [
            'Mission 35 is active.',
            'Complete the design screen, both oxygen curves and objective audit.',
            'Do not confuse product maximum with a growth-compatible design.',
        ]
        completed_dialogue = [
            'E. coli certification complete.',
            'Golden LabHero, the Golden Lab and the yeast programme are unlocked.',
            'Your next training phase begins with a new metabolic model.',
        ]

        self.input()
        if '35' in self.missions_completed:
            self.menu_message(completed_dialogue, buttons=False)
        elif '35' in self.missions_activated:
            self.menu_message(active_dialogue, menu_to_open=self.menu35)
        elif is_mission35_unlocked(self.missions_completed):
            self.menu_message(intro_dialogue, menu_to_open=self.menu35)
        else:
            self.menu_message(locked_dialogue, buttons=False)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, menu_to_open=None):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        image = get_dialogue_portrait(get_resource_path('graphics/dialogues/richter.jpg'), (150, 150))
        self.screen.blit(image, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_name, 'Dr. Richter')
        self.screen.blit(name, (48, 677))

        for line, message_line in enumerate(message):
            message_line = prepare_dialogue_text(message_line, self.player.player_name)
            surface = get_dialogue_text_surface(self.font, message_line)
            self.screen.blit(surface, (200, 525 + (line * 35)))

        if buttons:
            def click_yes():
                self.pending = (menu_to_open or self.menu35).update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission35_info:
    """Mission 35 — E. coli Final Systems Certification."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission35 = '35' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '35', self.missions_completed, mytheme)

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
            title='Mission 35',
            width=1280,
        )

        if not is_mission35_unlocked(self.missions_completed):
            menu.add.vertical_margin(40)
            menu.add.label(
                "Mission 35 is locked. Complete Mission 34 and Dr. Chen's programme first.",
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_CENTER,
                padding=(25, 25, 25, 25),
                background_color='white',
                font_size=30,
            )
            menu.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
            await run_menu(menu, self.display_surface)
            return

        design_lines = '\n'.join(
            f'- {MISSION35_DESIGN_LABELS[condition_id]}'
            for condition_id in MISSION35_DESIGN_ORDER
        )
        sweep_values = ', '.join(f'{value:g}' for value in MISSION35_SWEEP_VALUES)
        production_panel = ', '.join(MISSION35_REQUIRED_PRODUCTION_FLUXES)

        hint3 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 35 Hint 3', width=1280,
        )
        hint3.add.label(
            f'Technical hint: design screen = {MISSION35_METHOD}, biomass objective, default environment and exactly {production_panel}. For robustness, run two EX_o2_e lower-bound sweeps using the "Final oxygen convergence" preset ({sweep_values}) with b0114 and b0116. For the final audit, return to the default environment, keep b0114, use {MISSION35_METHOD}, and change the objective to {MISSION35_FORMATE_OBJECTIVE}.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 35 Hint 2', width=1280,
        )
        hint2.add.label(
            'Experimental hint: a qualifying design must satisfy all three approval criteria at once. In the oxygen curves, compare matched rows rather than only endpoints. For the objective audit, compare direct formate maximisation with the same genotype under the biomass objective.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 35 Hint 1', width=1280,
        )
        hint1.add.label(
            'Conceptual hint: this is a certification dossier, not a highest-number contest. Integrate production, growth retention, GPR reaction impact, oxygen-response behaviour and objective choice before deciding.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 35 Final Briefing', width=1280,
        )
        briefing.add.label(
            f"""
            Final E. coli certification has three linked evidence sections.

            A — Design Approval Screen
            - Method: {MISSION35_METHOD}
            - Objective: {MISSION35_GROWTH_OBJECTIVE}
            - Environment: completely model-default and aerobic
            - Production Flux: {production_panel}
            - Record in any order:
            {design_lines}
            - Approval: formate >= {MISSION35_APPROVAL_MIN_FORMATE:.1f}; growth retention >= {MISSION35_APPROVAL_MIN_GROWTH_RETENTION * 100:.0f}%; no more than {MISSION35_APPROVAL_MAX_DISABLED_REACTIONS} GPR-disabled reaction.

            B — Oxygen Robustness Curves
            - Compare b0114 with b0116
            - Method/objective: {MISSION35_METHOD} / biomass
            - Base environment: completely default
            - Bound Sweep variable: EX_o2_e lower bound
            - Preset: Final oxygen convergence ({sweep_values})
            - Use the full visible curve, and keep the GPR mechanism in view.

            C — Objective Viability Audit
            - Use b0114 in the completely default environment
            - Method: {MISSION35_METHOD}
            - Objective: {MISSION35_FORMATE_OBJECTIVE}
            - Compare the direct product optimum with the biomass-objective evidence already recorded in Section A.

            Deliver only after all three sections report complete evidence.
            """,
            max_char=-1, wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        menu.add.vertical_margin(20)
        menu.add.label('Mission 35: E. coli Final Systems Certification', align=pygame_menu.locals.ALIGN_CENTER, font_size=34)
        menu.add.label(
            'Integrate design, GPR, environmental robustness and objective choice in one final dossier.',
            wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_size=28,
        )
        menu.add.button('Final Mission Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        report = load_mission35_final_certification()
        report_options = {
            'wordwrap': True,
            'align': pygame_menu.locals.ALIGN_LEFT,
            'padding': (20, 20, 20, 20),
            'font_size': 21,
        }
        if report:
            report_options['background_color'] = 'white'
        menu.add.label(build_mission35_final_certification_report_text(report), **report_options)
        menu.add.vertical_margin(20)

        if '35' in self.missions_completed:
            rewards = mission35_reward_state(self.missions_completed)
            menu.add.label('Mission Completed', font_color=(40, 120, 40))
            if rewards.get('golden_skin_unlocked'):
                menu.add.label(
                    'Golden LabHero unlocked. Press C outside this menu to equip it.',
                    wordwrap=True, align=pygame_menu.locals.ALIGN_CENTER, font_color=(160, 110, 0),
                )
        elif self.mission35 or '35' in self.missions_activated:
            self.mission35 = True
            menu.add.label(
                'Final certification answers — derive all three from the completed visible dossier.',
                wordwrap=True, align=pygame_menu.locals.ALIGN_LEFT, font_size=24,
            )
            target_input = menu.add.text_input(
                'Approved reaction target: ', default='', input_underline='_', maxchar=36,
            )
            bound_input = menu.add.text_input(
                'First phenotype-convergence O2 lower bound: ', default='', input_underline='_', maxchar=16,
            )
            viability_input = menu.add.text_input(
                'Direct formate optimum growth-compatible? ', default='', input_underline='_', maxchar=28,
            )

            def deliver_from_fields():
                self.deliver_results(
                    target_input.get_value(),
                    bound_input.get_value(),
                    viability_input.get_value(),
                )

            menu.add.button('Deliver Final Dossier', deliver_from_fields, background_color=(50, 100, 100))
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission35, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission35(self):
        if not is_mission35_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 34 before starting the final certification.', time=3000)
            return
        if '35' in self.missions_completed:
            return
        if '35' in self.missions_activated:
            self.mission35 = True
            return
        clear_mission35_final_certification()
        initialise_mission35_final_certification()
        self.mission35 = True
        self.missions_activated.insert(0, '35')
        animation_text_save('Mission 35 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, target_answer, bound_answer, viability_answer):
        if not is_mission35_unlocked(self.missions_completed):
            self.failed.play()
            animation_text_save('Complete Mission 34 first!', time=2500)
            return
        if '35' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 35 before delivering the final dossier.', time=3000)
            return

        report = load_mission35_final_certification()
        if (
            not report
            or report.get('mission_id') != '35'
            or report.get('check_version') != MISSION35_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Record the current-format Mission 35 dossier first.', time=3000)
            return
        if not report.get('ready_to_deliver'):
            self.failed.play()
            animation_text_save('Complete all three Mission 35 evidence sections first.', time=3000)
            return

        checks = mission35_answer_checks(target_answer, bound_answer, viability_answer, report)
        if not checks.get('target'):
            self.failed.play()
            animation_text_save('Recheck which reaction target satisfies all design criteria.', time=3000)
            return
        if not checks.get('bound'):
            self.failed.play()
            animation_text_save('Recheck the first tested oxygen bound where the visible phenotypes converge.', time=3200)
            return
        if not checks.get('viability'):
            self.failed.play()
            animation_text_save('Recheck whether direct formate maximisation retains viable predicted growth.', time=3200)
            return
        if not mission35_answers_match(target_answer, bound_answer, viability_answer, report):
            self.failed.play()
            animation_text_save('The final dossier answers do not yet match the accumulated evidence.', time=3000)
            return

        self.success.play()
        if '35' not in self.missions_completed:
            self.missions_completed.insert(0, '35')
        save_file(self.player.get_save_data())
        animation_text_save(
            'E. coli certification complete! Golden LabHero unlocked — press C to equip it.',
            time=3800,
        )

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            pass

    async def update(self):
        self.input()
        await self.setup()
