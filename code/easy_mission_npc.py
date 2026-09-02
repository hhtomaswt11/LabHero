import pygame

from button import Button
from settings import *
from timers import Timer
from utils import *


EASY_NPC_CONFIG = {
    '01': {
        'scientist': 'Dr. Martinez', 'portrait': 'martinez.jpg',
        'intro': [
            "Welcome to the Easy campaign. I'm Dr. Martinez.",
            "Start with one controlled oxygen experiment in E. coli.",
            "Use the simulator evidence to compare aerobic and anaerobic growth.",
        ],
        'active': [
            "Mission 01 is active.",
            "Keep the model setup controlled and change only oxygen availability.",
            "Return with the visible simulation evidence.",
        ],
        'completed': [
            "Excellent. You have completed the environmental introduction.",
            "Continue to Dr. Silva for the gene-perturbation mission.",
        ],
    },
    '03': {
        'scientist': 'Dr. Silva', 'portrait': 'silva.jpg',
        'intro': [
            "Welcome. In this shorter route we move directly to gene perturbation.",
            "Mission 03 asks you to identify a conditionally essential gene.",
            "Use a viable reference and controlled single-gene knockouts.",
        ],
        'active': [
            "Mission 03 is active.",
            "Compare the reference with each candidate knockout under the same environment.",
            "Return when the growth ratios support one conclusion.",
        ],
        'completed': [
            "Excellent. You identified conditional gene essentiality.",
            "Dr. Carter will now combine genetic changes with production trade-offs.",
        ],
    },
    '06': {
        'scientist': 'Dr. Carter', 'portrait': 'carter.jpg',
        'intro': [
            "Now test a controlled multi-knockout design.",
            "Mission 06 balances predicted growth with ethanol production.",
            "A larger product flux is not automatically the best overall design.",
        ],
        'active': [
            "Mission 06 is active.",
            "Compare the requested designs using the same conditions and visible evidence.",
            "Return with the design supported by the mission's balance criterion.",
        ],
        'completed': [
            "Good work. You handled a growth-production trade-off.",
            "Proceed to Dr. Nova to study the effect of the objective function itself.",
        ],
    },
    '07': {
        'scientist': 'Dr. Nova', 'portrait': 'nova.jpg',
        'intro': [
            "Mission 07 isolates one fundamental modelling choice: the objective function.",
            "Compare biomass optimisation with direct ethanol optimisation.",
            "Keep the strain, medium and method unchanged.",
        ],
        'active': [
            "Mission 07 is active.",
            "Change only the objective and compare biomass, ethanol and oxygen evidence.",
            "Return when you can explain why the two optima differ.",
        ],
        'completed': [
            "Excellent. You showed that the objective changes the optimisation question.",
            "Continue to Dr. Almeida for a direct FBA-versus-pFBA comparison.",
        ],
    },
    '13': {
        'scientist': 'Dr. Almeida', 'portrait': 'almeida.jpg',
        'intro': [
            "In the Easy route we begin my lab with Mission 13.",
            "Use one anaerobic succinate-optimisation setup and compare FBA with pFBA.",
            "Separate the primary objective from pFBA's parsimony criterion.",
        ],
        'active': [
            "Mission 13 is active.",
            "Keep the same succinate objective and anaerobic environment for both methods.",
            "Use Production Flux evidence to support the comparison.",
        ],
        'completed': [
            "Excellent. You distinguished objective optimisation from flux parsimony.",
            "Continue to Dr. Rio for a binding-versus-non-binding constraint experiment.",
        ],
    },
    '18': {
        'scientist': 'Dr. Rio', 'portrait': 'rio.jpg',
        'intro': [
            "In the Easy route we start my lab with Mission 18.",
            "Test when an export upper bound actually changes the predicted phenotype.",
            "The key distinction is configured constraint versus binding constraint.",
        ],
        'active': [
            "Mission 18 is active.",
            "Record the anaerobic export baseline, then test the requested upper-bound closures.",
            "Compare predicted growth rate and the complete visible product profile.",
        ],
        'completed': [
            "Excellent. You showed that a bound matters only when it constrains used flux.",
            "Dr. Vega will now study compensatory flux redistribution.",
        ],
    },
    '21': {
        'scientist': 'Dr. Vega', 'portrait': 'vega.jpg',
        'intro': [
            "Mission 21 is a controlled before-and-after comparison.",
            "Close one active export route and identify the strongest compensatory secretion.",
            "Change only the requested export bound between the two runs.",
        ],
        'active': [
            "Mission 21 is active.",
            "Record the anaerobic reference and modified run.",
            "Return with the flux difference supported by the visible evidence.",
        ],
        'completed': [
            "Excellent. You quantified a compensatory redistribution of flux.",
            "Continue to Dr. Luna for a graded nutrient-sensitivity sweep.",
        ],
    },
    '23': {
        'scientist': 'Dr. Luna', 'portrait': 'luna.jpg',
        'intro': [
            "Mission 23 introduces a Bound Sweep.",
            "Test controlled ammonium levels and follow the response across the curve.",
            "Distinguish the configured bound from the uptake the solution actually uses.",
        ],
        'active': [
            "Mission 23 is active.",
            "Configure the ammonium sweep and inspect every response row.",
            "Return with the secretion supported by the onset of nutrient limitation.",
        ],
        'completed': [
            "Excellent. You interpreted a response across graded perturbation levels.",
            "Dr. Smith will now test how gene effects depend on environmental context.",
        ],
    },
    '25': {
        'scientist': 'Dr. Smith', 'portrait': 'smith.jpg',
        'intro': [
            "Mission 25 tests context-dependent gene essentiality.",
            "Compare wild type and knockout under aerobic and anaerobic conditions.",
            "Use the complete matrix before making an essentiality claim.",
        ],
        'active': [
            "Mission 25 is active.",
            "Complete every oxygen-by-genotype condition under the same protocol.",
            "Return when the evidence supports one context-dependent conclusion.",
        ],
        'completed': [
            "Excellent. You showed that gene essentiality depends on modelling context.",
            "Continue to Dr. Ribeiro for a metabolic-rescue experiment.",
        ],
    },
    '27': {
        'scientist': 'Dr. Ribeiro', 'portrait': 'ribeiro.jpg',
        'intro': [
            "Mission 27 asks whether the environment can rescue a genetic failure.",
            "Keep the gltA knockout fixed and test one candidate supplement at a time.",
            "A rescue must restore growth while citrate synthase remains disabled.",
        ],
        'active': [
            "Mission 27 is active.",
            "Keep the lesion fixed and compare the requested supplements fairly.",
            "Return with the rescue supported by predicted growth and GPR evidence.",
        ],
        'completed': [
            "Excellent. You restored predicted growth without repairing the deleted gene.",
            "The Golden Lab is now the final stage of your Easy campaign.",
        ],
    },
    '36': {
        'scientist': 'Vale', 'portrait': 'vale.jpg',
        'intro': [
            "Welcome to the final Easy-campaign experiment.",
            "Apply the same modelling discipline to the larger yeast iMM904 model.",
            "Use pFBA and a glucose sweep to identify the onset of fermentation.",
        ],
        'active': [
            "Mission 36 is active.",
            "Build the default pFBA reference, then run the glucose threshold sweep.",
            "Compare realised oxygen uptake with ethanol secretion across the tested bounds.",
        ],
        'completed': [
            "Excellent. You completed the curated Easy campaign.",
            "You applied environment, genetics, objectives, constraints and sweeps across two models.",
            "Close this dialogue to view your final campaign results.",
        ],
    },
}


class EasyMissionNPC:
    """Single-mission NPC presentation used only by the curated Easy route.

    Normal keeps every original multi-mission controller untouched.  This class
    prevents skipped Easy missions from leaking through those historic chains.
    """

    def __init__(self, toggle_menu, player, mission_id):
        self.toggle_menu = toggle_menu
        self.player = player
        self.mission_id = str(mission_id).zfill(2)
        if self.mission_id not in EASY_NPC_CONFIG:
            raise ValueError(f'No Easy NPC configuration for Mission {self.mission_id}')
        self.config = EASY_NPC_CONFIG[self.mission_id]
        self.screen = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        self.font_name = pygame.font.Font(font_path, 24)
        self.timer = Timer(200)
        self.pending = None

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    def _mission_menu(self):
        # Direct lazy imports preserve the project's proven Pygbag import model.
        if self.mission_id == '01':
            from mission01 import Mission_info
            return Mission_info(self.toggle_menu, self.player)
        if self.mission_id == '03':
            from mission03 import Mission03_info
            return Mission03_info(self.toggle_menu, self.player)
        if self.mission_id == '06':
            from mission06 import Mission06_info
            return Mission06_info(self.toggle_menu, self.player)
        if self.mission_id == '07':
            from mission07 import Mission07_info
            return Mission07_info(self.toggle_menu, self.player)
        if self.mission_id == '13':
            from mission13 import Mission13_info
            return Mission13_info(self.toggle_menu, self.player)
        if self.mission_id == '18':
            from mission18 import Mission18_info
            return Mission18_info(self.toggle_menu, self.player)
        if self.mission_id == '21':
            from mission21 import Mission21_info
            return Mission21_info(self.toggle_menu, self.player)
        if self.mission_id == '23':
            from mission23 import Mission23_info
            return Mission23_info(self.toggle_menu, self.player)
        if self.mission_id == '25':
            from mission25 import Mission25_info
            return Mission25_info(self.toggle_menu, self.player)
        if self.mission_id == '27':
            from mission27 import Mission27_info
            return Mission27_info(self.toggle_menu, self.player)
        if self.mission_id == '36':
            from mission36 import Mission36_info
            return Mission36_info(self.toggle_menu, self.player)
        raise ValueError(f'Unsupported Easy mission {self.mission_id}')

    async def update(self):
        self.input()
        if self.mission_id in self.player.missions_completed:
            self.menu_message(self.config['completed'], buttons=False)
        elif self.mission_id in self.player.missions_activated:
            self.menu_message(self.config['active'])
        elif self.player.is_mission_unlocked(self.mission_id):
            self.menu_message(self.config['intro'])
        else:
            requirement = self.player.get_campaign_context().previous_mission(self.mission_id)
            if requirement is None:
                locked = ['This Easy-campaign mission is not available yet.']
            else:
                locked = [
                    f'Mission {self.mission_id} is still locked.',
                    f'Complete Mission {requirement} first in your Easy campaign.',
                ]
            self.menu_message(locked, buttons=False)

        if self.pending is not None:
            coro = self.pending
            self.pending = None
            await coro()

    def menu_message(self, message, buttons=True):
        pygame.draw.rect(self.screen, (255, 215, 0), [0, 500, 1280, 220], width=5)
        pygame.draw.rect(self.screen, (186, 214, 177), [5, 505, 1270, 210])
        image = get_dialogue_portrait(
            get_resource_path(f"graphics/dialogues/{self.config['portrait']}"),
            (150, 150),
        )
        self.screen.blit(image, (25, 520))
        pygame.draw.rect(self.screen, 'white', [25, 675, 150, 25])
        name = get_dialogue_text_surface(self.font_name, self.config['scientist'])
        self.screen.blit(name, (38, 677))

        for line, text in enumerate(message):
            text = prepare_dialogue_text(text, self.player.player_name)
            self.screen.blit(
                get_dialogue_text_surface(self.font, text),
                (200, 525 + line * 35),
            )

        if buttons:
            def click_yes():
                menu = self._mission_menu()
                self.pending = menu.update

            Button(200, 650, 150, 50, self.screen, 'Yes', click_yes).process()
            Button(370, 650, 220, 50, self.screen, 'Not now', self.toggle_menu).process()
        pygame.display.flip()
