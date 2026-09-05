import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from button import Button
from utils import *
from hint_system import (
    SCORE_BY_HINT_LEVEL,
    WRONG_ANSWER_PENALTY,
    initial_keys_for_campaign,
)

class Dialogues: 
    def __init__(self,toggle_menu, player) -> None: # add variable name character to change message and id
        #general setup 
        self.player = player
        self.character = None
        # Track which generic NPC has already had its static dialogue state prepared.
        # A dedicated sentinel preserves the old fallback behaviour even if the first
        # call unexpectedly passes None.
        self._prepared_character = object()

        self.toggle_menu = toggle_menu

        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path,30)
        self.font_nome = pygame.font.Font(font_path,24)
        self.screen = pygame.display.get_surface() 
        self.timer = Timer(200)
        self.imagem_path = None
        self.nome = None



    def choosing_character(self, character):
        # Most generic NPC dialogue is static and can be prepared once.
        # Easter Man reacts to Golden Egg/campaign state, so include those
        # values in his cache key and allow the dialogue to change later.
        if character == 'easter_man':
            preparation_key = (
                character,
                bool(getattr(self.player, 'golden_egg_collected', False)),
                bool(self.player.get_campaign_context().is_campaign_complete(
                    self.player.missions_completed
                )),
            )
        else:
            preparation_key = character

        if preparation_key == self._prepared_character:
            return

        self.character = character
        if self.character == 'Sequeira':    
            self.message = [
            "Hello! I am Dr. João Sequeira, and my research focuses on meta-omics,",
            "which means I study complex microbial communities through their collective DNA, RNA",
             "and proteins!",
             " ",
            "By combining these layers, we can study microbial communities as interacting systems."
        ]
            self.imagem_path = get_resource_path('graphics/dialogues/Sequeira.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Sequeira')
            
        elif self.character == 'Alves':  # legacy internal id for the Dr. Melo start NPC
            mode = self.player.campaign_mode
            budget = initial_keys_for_campaign(mode)
            current = {
                key: self.player.hint_system.get_key_count(key)
                for key in ('bronze', 'silver', 'gold')
            }
            self.message = [
                f"Registration complete, {self.player.player_name}. Mode: {self.player.campaign_mode.title()}.",
                f"Your route starts with {budget['bronze']} Bronze, {budget['silver']} Silver and {budget['gold']} Gold keys.",
                f"Current keys: {current['bronze']} Bronze, {current['silver']} Silver, {current['gold']} Gold. Each hint spends one.",
                f"Hints reduce mission score: {SCORE_BY_HINT_LEVEL[0]} -> {SCORE_BY_HINT_LEVEL[1]} -> {SCORE_BY_HINT_LEVEL[2]} -> {SCORE_BY_HINT_LEVEL[3]}.",
                f"Incorrect final-answer submission: -{WRONG_ANSWER_PENALTY} point, even for a typo. Minimum score: 0."
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/melo.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Melo')

        elif self.character == 'Nuno':    
            self.message = [
            "Hello! My name is Dr. Nuno Alves!",
            " ",
            "I'm currently doing my PhD where I'm trying to use Artificial Intelligence",
            "to find novel antibiotics for Mycobacterium tuberculosis."
        ]
            self.imagem_path = get_resource_path('graphics/dialogues/Nuno.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Alves')
        elif self.character == 'Pacheco':
            self.message = [
            "Oh hello, fellow student! My name is Dr. Miguel Pacheco and I'm trying to improve the",
            "production of bacterial cellulose. For that, I'm building a genome-scale metabolic model",
            "and carrying out laboratory experiments to test the model's predictions.",
            "in my quest! Let's both try our best!"
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Pacheco.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Pacheco')

        elif self.character == 'Marta':
            self.message = [
            "I’m Marta Sampaio, and I developed a Genome-scale metabolic model to study how",
            "grapevines grow and change throughout the day and night.",
            "This helps us connect metabolism with how the plant responds across the day."
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Marta.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dra. Sampaio')
        
        elif self.character == 'Capela':
            self.message = [
            "Hi, I’m João Capela! I am a bioinformatics and plant enthusiast,",
            "so why not combine the two?",
            "I’m currently exploring AI and systems biology methods to decipher",
            "plant specialized metabolism!"
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Capela.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Capela')

        elif self.character == 'Fernanda':
            self.message = [
            "Hey there! I am Dr. Fernanda Vieira and my research focuses on phage therapy.",
            "This means I explore the intricate world of viral communities, specifically phages,",
            "by studying their interactions with the host organisms.",
            "Interesting, right?"
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Fernanda.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dra. Vieira')

        elif self.character == 'Alexandre':
            self.message = [
            "Hello there! My name is Dr. Alexandre Oliveira, and I am studying the metabolic",
            "interactions between SARS-CoV-2 and various human tissues using genome-scale",
            "metabolic models.",
            "SARS-CoV-2 is the coronavirus that causes COVID-19."
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Alexandre.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Oliveira')

        elif self.character == 'Emanuel':
            self.message = [
            "Hey there! I am Dr. Emanuel Cunha, and my line of research is systems biology.",
            "Currently, I'm studying pigment and lipid production by microalgae using",
            "genome-scale metabolic models.",
            "Do you already know what GEMs are?"
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Emanuel.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Cunha')
        elif self.character == 'Oscar':
            self.message = [
            "Hello! I’m Oscar Dias, and I study how living systems",
            "work using computational and mathematical methods. ",
            "In our lab, data and models help us investigate complex biological questions. ",
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Oscar.jpg') 
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Dias')
        elif self.character == 'Miguel':
            self.message = [
            "Hi there! I’m Miguel Rocha, and I study how computers can help us understand ",
            "and solve problems in biology and medicine. ",
            "The goal is to turn biological data into models that can support useful predictions."
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/Miguel.jpg') 
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr. Rocha')

        elif self.character == 'isabel':
            self.message = [
                "I’m Isabel Rocha. In a Portuguese systems-biology lab, my name may sound familiar.",
                "I helped create OptFlux, an open-source platform for in silico metabolic engineering.",
                "OptFlux turned genome-scale models into practical tools for strain design.",
                "You finished E. coli training; carry that design mindset into the Golden Lab.",
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/isabel_rocha.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Isabel Rocha')

        elif self.character == 'bernhard':
            self.message = [
                "I’m Bernhard O. Palsson. I study what cells can do within biological constraints.",
                "My group helped establish COBRA for genome-scale reconstruction and analysis.",
                "Stoichiometry, bounds and gene deletions are all part of that COBRA lineage.",
                "Models become powerful when constraints turn biological ideas into predictions.",
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/bernhard_palsson.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'B. O. Palsson')

        elif self.character == 'jens':
            self.message = [
                "I’m Jens Nielsen. My work connects systems biology with metabolic engineering.",
                "Yeast has been a major focus of my work, from models to strain design.",
                "Saccharomyces cerevisiae can be a cell factory for fuels, chemicals and proteins.",
                "Your next missions move to yeast, so ask what each prediction could help you design.",
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/jens_nielsen.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Jens Nielsen')

        elif self.character == 'chris':
            self.message = [
                "I’m Christopher Henry — Chris is fine. I build metabolic models at large scale.",
                "I developed ModelSEED to automate genome-scale metabolic model reconstruction.",
                "That work also connects with KBase, bringing models and genomic tools together.",
                "Every simulation starts by turning biological knowledge into a computable network.",
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/chris_henry.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Chris Henry')

        elif self.character == 'ahmad':
            self.message = [
                "I’m Ahmad Zeidan. My work connects systems biology with industrial biotechnology.",
                "I use genome-scale and constraint-based models to understand industrial microbes.",
                "In food biotechnology, models can connect microbial traits with practical decisions.",
                "Predictions matter most when they guide real biological or biotechnological choices.",
            ]
            self.imagem_path = get_resource_path('graphics/dialogues/ahmad_zeidan.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Ahmad Zeidan')

        elif self.character == 'easter_man':
            egg_found = bool(getattr(self.player, 'golden_egg_collected', False))
            campaign_complete = self.player.get_campaign_context().is_campaign_complete(
                self.player.missions_completed
            )

            if egg_found and not campaign_complete:
                self.message = [
                    "So... you found it. Good. Curiosity still counts for something around here.",
                    "Keep what it gave you close; the next experiments may make you glad you explored.",
                    "Some of the best rewards are hidden just beyond the obvious path.",
                    "And if anyone asks what I meant... we never spoke.",
                ]
            elif not egg_found and not campaign_complete:
                self.message = [
                    "Hmm... some things are easier to miss than to find.",
                    "Funny how something valuable can hide in plain sight.",
                    "Perhaps exploration is not your strongest skill after all.",
                    "Either way, the next experiments may make you wish you had looked a little harder.",
                ]
            elif egg_found:
                self.message = [
                    "So you found it before the end. Good. I knew curiosity might pay off.",
                    "I hope those golden keys were worth the detour.",
                    "The best discoveries are not always part of the assignment.",
                    "Do not worry — I will not tell anyone how close you came to missing it.",
                ]
            else:
                self.message = [
                    "Still looking for it? Ah... then you are a little late.",
                    "Some rewards are useful only before the final experiment is finished.",
                    "Perhaps exploration really was not your strongest trait after all.",
                    "No matter. Next time, remember to look where the mission marker does not point.",
                ]

            self.imagem_path = get_resource_path('graphics/dialogues/easter_man.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, '???')

        else:
            self.message = ['Hello there! Are you enjoying LabHero so far?']
            self.imagem_path = get_resource_path('graphics/dialogues/carter.jpg')
            self.nome = get_dialogue_text_surface(self.font_nome, 'Dr.')

        # Mark the character as prepared only after its complete static state exists.
        self._prepared_character = preparation_key


    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    def update(self):
        self.input()
        self.menu_message(self.message, buttons=False)


    def menu_message(self, message, buttons = False):

        menu_border = pygame.draw.rect(self.screen, (255,215,0), [0,500,1280,220], width=5)
        menu_bg = pygame.draw.rect(self.screen, (186,214,177), [5,505,1270,210])

        imagem = get_dialogue_portrait(self.imagem_path)
        
        x = 25; # x coordnate of image
        y = 520; # y coordinate of image
        self.screen.blit(imagem, ( x,y))

        cientista_rect = pygame.draw.rect(self.screen, 'white', [25,675,150,25])

        # nome = self.font_nome.render('Dr. Sequeira', True, 'black')
        self.screen.blit(self.nome,(40,677))

        for line, msg in enumerate(message):
            surf = get_dialogue_text_surface(self.font, msg)
            self.screen.blit(surf,(200,525+(line*20)+(15*line)))

        if buttons:
            botao_teste = Button(200,650,150,50,self.screen, 'Yes', self.menu.update)
            botao_teste_2 = Button(370,650,220,50,self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        

        pygame.display.flip()

