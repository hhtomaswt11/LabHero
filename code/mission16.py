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
    MISSION16_CHECK_VERSION,
    MISSION16_METHOD,
    MISSION16_GROWTH_OBJECTIVE,
    MISSION16_BLOCKED_CARBON_SOURCE,
    MISSION16_OXYGEN_REACTION,
    MISSION16_CANDIDATE_CARBON_SOURCES,
    MISSION16_SOURCE_NAMES,
    MISSION16_EXPECTED_SOURCE_UPTAKE,
    build_mission16_context_report_text,
    initialise_mission16_context_rescue,
    is_mission16_unlocked,
    mission16_answer_matches,
    normalise_mission16_answer,
    MISSION19_BASELINE_METHOD,
    MISSION19_TARGET_METHOD,
    MISSION19_TARGET_GENE,
    MISSION19_TARGET_GENE_NAME,
    MISSION20_TARGET_METHOD,
    MISSION20_OXYGEN_REACTION,
    MISSION20_ACETATE_EXPORT,
)
from mission17 import Mission17_info
from mission18 import Mission18_info
from mission19 import Mission19_info
from mission20 import Mission20_info


class Mission16:
    """Dr. Rio mission chain, beginning with Mission 16."""

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

        self.menu = Mission16_info(self.toggle_menu, self.player)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        locked_dialogue = [
            "Dr. Almeida is still completing your objective-conflict training.",
            "Complete Mission 15 before beginning Dr. Rio's medium-engineering programme.",
        ]

        self.m16_step1 = [
            f"Hello {self.player.player_name}. I'm Dr. Rio.",
            "Dr. Almeida showed that one optimum does not establish a robust design.",
            "Now we will test how carbon rescue changes with the surrounding medium."
        ]

        self.m16_step2 = [
            "Mission 16 is active. Screen five alternative carbon sources fairly.",
            "Then repeat the strongest-growth source after closing oxygen uptake.",
            "Use the Exchange Flux Report and visible solver status as evidence."
        ]

        self.m16_step3 = [
            f"Excellent work, {self.player.player_name}.",
            "You showed that a strong carbon rescue can fail when the medium changes.",
            "Next we will test whether every medium component is optional."
        ]

        self.m17_step1 = [
            "Mission 17 is active. Record one complete default-medium baseline.",
            "Then close one candidate lower bound per run and compare growth.",
            "Use signed exchange fluxes to distinguish uptake from secretion."
        ]

        self.m17_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You identified which lower-bound closures remove required uptake routes.",
            "Next, use an upper bound to create a controlled export bottleneck."
        ]

        self.m18_step1 = [
            f"Great progress, {self.player.player_name}.",
            "Lower bounds controlled uptake in the previous screen.",
            "Now test how an upper bound can constrain secretion and export."
        ]

        self.m18_step2 = [
            "Mission 18 is active. Record one anaerobic export baseline.",
            "Then close two candidate upper bounds in separate controlled runs.",
            "Compare growth and the complete visible product profile."
        ]

        self.m18_step3 = [
            f"Excellent work, {self.player.player_name}.",
            "You showed that a constraint matters only when the baseline uses that flux.",
            "Now let's test how the model responds to a genetic perturbation."
        ]

        self.m19_step1 = [
            f"Mission 19 is active. Record a wild-type {MISSION19_BASELINE_METHOD} baseline.",
            f"Then compare the same {MISSION19_TARGET_GENE} knockout under FBA and {MISSION19_TARGET_METHOD}.",
            "Keep every other setting fixed and compare visible biomass and method diagnostics."
        ]

        self.m19_step2 = [
            f"Excellent method comparison, {self.player.player_name}.",
            f"You separated re-optimised FBA from the minimal-adjustment {MISSION19_TARGET_METHOD} response.",
            "One final Dr. Rio robustness challenge remains."
        ]

        self.m20_step1 = [
            "Mission 20 is active. Build a four-run context-robustness matrix.",
            f"Use {MISSION20_TARGET_METHOD} and vary only {MISSION20_OXYGEN_REACTION} uptake",
            f"and the {MISSION20_ACETATE_EXPORT} export upper bound between controlled runs."
        ]

        self.m20_step2 = [
            f"Excellent work, {self.player.player_name}.",
            "You showed that one export constraint can behave differently",
            "across controlled oxygen contexts.",
            "Dr. Vega will formalise comparisons in the next laboratory."
        ]

        self.input()
        if not self.player.is_mission_unlocked('16'):
            self.menu_message(locked_dialogue, buttons=False)
        elif '20' in self.missions_completed:
            self.menu_message(self.m20_step2, buttons=False)
        elif '19' in self.missions_completed and '20' in self.missions_activated:
            self.menu_message(self.m20_step1, target_mission='20')
        elif '19' in self.missions_completed:
            self.menu_message(self.m19_step2, target_mission='20')
        elif '18' in self.missions_completed and '19' in self.missions_activated:
            self.menu_message(self.m19_step1, target_mission='19')
        elif '18' in self.missions_completed:
            self.menu_message(self.m18_step3, target_mission='19')
        elif '17' in self.missions_completed and '18' in self.missions_activated:
            self.menu_message(self.m18_step2, target_mission='18')
        elif '17' in self.missions_completed:
            self.menu_message(self.m18_step1, target_mission='18')
        elif '16' in self.missions_completed and '17' in self.missions_activated:
            self.menu_message(self.m17_step1, target_mission='17')
        elif '16' in self.missions_completed:
            self.menu_message(self.m16_step3, target_mission='17')
        elif '16' in self.missions_activated:
            self.menu_message(self.m16_step2)
        else:
            self.menu_message(self.m16_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()

    def menu_message(self, message, buttons=True, target_mission='16'):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])

        imagem_path = get_resource_path('graphics/dialogues/rio.jpg')
        imagem = get_dialogue_portrait(imagem_path, (150, 150))
        self.screen.blit(imagem, (25, 520))

        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        nome = get_dialogue_text_surface(self.font_nome, 'Dr. Rio')
        self.screen.blit(nome, (56, 677))

        for line, msg in enumerate(message):
            msg = prepare_dialogue_text(msg, self.player.player_name)
            surf = get_dialogue_text_surface(self.font, msg)
            self.screen.blit(surf, (200, 525 + (line * 20) + (15 * line)))

        if buttons:
            def click_yes():
                if target_mission == '20':
                    mission20_menu = Mission20_info(self.toggle_menu, self.player)
                    self.pending = mission20_menu.update
                elif target_mission == '19':
                    mission19_menu = Mission19_info(self.toggle_menu, self.player)
                    self.pending = mission19_menu.update
                elif target_mission == '18':
                    mission18_menu = Mission18_info(self.toggle_menu, self.player)
                    self.pending = mission18_menu.update
                elif target_mission == '17':
                    mission17_menu = Mission17_info(self.toggle_menu, self.player)
                    self.pending = mission17_menu.update
                else:
                    self.pending = self.menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()

        pygame.display.flip()


class Mission16_info:
    """Mission 16 — Context-Dependent Carbon Rescue."""

    def __init__(self, toggle_menu, player) -> None:
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.timer = Timer(200)
        self.mission16 = '16' in self.missions_activated
        self.hint_access = MissionHintAccess(self.player, '16', self.missions_completed, mytheme)

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
            title='Mission 16',
            width=1280,
        overflow=(False, True),
        )

        if not self.player.is_mission_unlocked('16'):
            menu.add.vertical_margin(40)
            menu.add.label(
                'Mission 16 is locked. Complete Mission 15 before beginning Dr. Rio medium engineering.',
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
            theme=mytheme, title='Mission 16 Hint 3', width=1280,
        overflow=(False, True),
        )
        hint3.add.label(
            f'Technical hint: use {MISSION16_METHOD}, objective {MISSION16_GROWTH_OBJECTIVE}, all genes active, close glucose uptake, and open exactly one of ' + ', '.join(MISSION16_CANDIDATE_CARBON_SOURCES) + f'. Keep oxygen at default for all five trials. Then repeat the highest-growth source after closing the lower bound of {MISSION16_OXYGEN_REACTION}.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint3.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint2 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 16 Hint 2', width=1280,
        overflow=(False, True),
        )
        hint2.add.label(
            'Experimental hint: use the same molar uptake protocol for every source. Compare predicted growth first, then change only oxygen availability in the robustness test.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint2.add.button('Reveal technical hint (Gold Key if locked)', self.hint_access.request, 3, hint2, hint3, background_color=(255, 215, 0), font_color='black')
        hint2.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        hint1 = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 16 Hint 1', width=1280,
        overflow=(False, True),
        )
        hint1.add.label(
            'Conceptual hint: a carbon source that supports the strongest growth in one medium may fail when another environmental requirement is removed.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        hint1.add.button('Reveal next hint (Silver Key if locked)', self.hint_access.request, 2, hint1, hint2, background_color=(255, 215, 0), font_color='black')
        hint1.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        briefing = pygame_menu.Menu(
            height=720, center_content=False, onclose=pygame_menu.events.BACK,
            theme=mytheme, title='Mission 16 Briefing', width=1280,
        overflow=(False, True),
        )
        briefing.add.label(
            f"""
            Dr. Almeida showed that an optimum must be audited against other biological requirements. Dr. Rio now wants a medium-context audit.

            Phase A — aerobic screen:
            Close glucose uptake and test each of the five candidate carbon sources separately. Use {MISSION16_METHOD}, the biomass objective, all genes active and the model-default oxygen supply. The same open lower-bound protocol corresponds to approximately {MISSION16_EXPECTED_SOURCE_UPTAKE:.1f} units of source uptake in these optimal solutions.

            Phase B — robustness challenge:
            Identify the uniquely strongest-growth source from the complete screen. Repeat that source with the same setup, but close oxygen uptake. Record the visible solver status.

            The final answer is deliberately short: name the environmental factor whose removal caused the strongest rescue to fail. The field accepts a factor name such as a reaction name or common abbreviation; it is not a free-form essay.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            padding=(20, 20, 20, 20),
        )
        briefing.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, briefing, hint1, background_color=(230, 230, 180), font_color='black')
        briefing.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        candidates_text = '   '.join(
            f"{MISSION16_SOURCE_NAMES.get(source_id, source_id)} ({source_id})"
            for source_id in MISSION16_CANDIDATE_CARBON_SOURCES
        )

        menu.add.vertical_margin(20)
        menu.add.label(
            'Mission 16: Context-Dependent Carbon Rescue',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34,
        )
        menu.add.label(
            'Screen five alternative carbon sources under one aerobic protocol, then challenge the strongest rescue by removing oxygen uptake.',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=27,
        )
        menu.add.label(
            f'Candidate sources:\n{candidates_text}',
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            font_size=24,
            padding=(5, 0, 0, 35),
        )
        menu.add.button('Mission 16 Briefing', briefing, font_color='black', background_color=(255, 215, 0))
        menu.add.button('Optional Hints (Bronze Key if locked)', self.hint_access.request, 1, menu, hint1, font_color='black', background_color=(230, 230, 180))
        menu.add.vertical_margin(25)

        if self.mission16:
            report = load_mission16_medium_report_check()
            if (
                not isinstance(report, dict)
                or report.get('mission_id') != '16'
                or report.get('check_version') != MISSION16_CHECK_VERSION
            ):
                report = initialise_mission16_context_rescue()
            menu.add.label(
                build_mission16_context_report_text(report),
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=22,
            )
            menu.add.vertical_margin(20)
            menu.add.label(
                'Question: Which removed environmental factor did the strongest rescue depend on?',
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                font_size=24,
            )
            menu.add.text_input(
                'Environmental factor: ',
                default='',
                input_underline='_',
                maxchar=30,
                onreturn=self.deliver_results,
            )
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
        else:
            menu.add.button('Activate Mission', action=self.activate_mission16, background_color=(50, 100, 100))

        menu.add.vertical_margin(20)
        await run_menu(menu, self.display_surface)

    def activate_mission16(self):
        if not self.player.is_mission_unlocked('16'):
            self.failed.play()
            animation_text_save('Complete Mission 15 before starting Mission 16.', time=3000)
            return
        if '16' in self.missions_completed:
            return
        if '16' in self.missions_activated:
            self.mission16 = True
            return

        clear_mission16_medium_report_check()
        initialise_mission16_context_rescue()
        self.mission16 = True
        self.missions_activated.insert(0, '16')
        animation_text_save('Mission 16 Activated')
        save_file(self.player.get_save_data())

    def deliver_results(self, answer):
        if not self.player.is_mission_unlocked('16'):
            self.failed.play()
            animation_text_save('Complete Mission 15 first!', time=2500)
            return
        if '16' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 16 before delivering a conclusion.', time=2800)
            return

        report = load_mission16_medium_report_check()
        if (
            not report
            or report.get('mission_id') != '16'
            or report.get('check_version') != MISSION16_CHECK_VERSION
        ):
            self.failed.play()
            animation_text_save('Build the complete Mission 16 screen first.', time=3000)
            return
        if not report.get('aerobic_screen_complete'):
            self.failed.play()
            animation_text_save('Record all five controlled aerobic source trials first.', time=3200)
            return
        if not report.get('oxygen_challenge_recorded'):
            self.failed.play()
            animation_text_save('Repeat the strongest source after closing oxygen uptake.', time=3200)
            return
        if not report.get('relationship_supported'):
            self.failed.play()
            animation_text_save('The final visible challenge does not support the expected context conclusion.', time=3300)
            return
        if normalise_mission16_answer(answer) is None:
            self.failed.play()
            animation_text_save('Enter the environmental factor removed in the final challenge.', time=3000)
            penalize_wrong_answer(self.player, '16')
            return
        if not mission16_answer_matches(answer, report):
            self.failed.play()
            animation_text_save('That factor is not supported by the recorded robustness test.', time=3000)
            penalize_wrong_answer(self.player, '16')
            return

        self.success.play()
        if '16' not in self.missions_completed:
            self.missions_completed.insert(0, '16')
        animation_text_save('Congratulations! Mission 16 completed!', time=2500)
        save_file(self.player.get_save_data())

    def input(self):
        self.timer.update()

    async def update(self):
        self.input()
        await self.setup()
