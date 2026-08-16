import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from button import Button
from utils import *
from async_menu import run_menu
from mission02 import Mission02_info

class Mission01: 
    def __init__(self, toggle_menu, player) -> None:
        #general setup 
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu

        font_path = get_resource_path('font/LycheeSoda.ttf')

        self.font = pygame.font.Font(font_path,30)
        self.font_nome = pygame.font.Font(font_path,24)
        self.screen = pygame.display.get_surface() 
        self.timer = Timer(200)

        self.menu = Mission_info(self.toggle_menu, self.player)
        self.pending = None


    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        self.m01_step1 = [
            f"Hello {self.player.player_name}! I'm Dr. Martinez.",
            "I study how E. coli adapts when its environment changes.",
            "Can you help me test one controlled condition?"
        ]
        
        self.m01_step2 = [
            "Have you already tested the environmental condition?",
            "Show me what the simulation revealed."
        ]


        # self.m01_step3 = ["Thank you! You're pioneering our understanding of E. coli's resilience.",
        #                   "Your discoveries will shape our research."]
        

        # self.input()
        # if '01' in self.missions_completed:
        #     self.menu_message(self.m01_step3, buttons=False)

        # elif '01' in self.missions_activated:
        #     self.menu_message(self.m01_step2)

        # else:
        #     self.menu_message(self.m01_step1)


        self.m01_step3 = [
            "Thank you! You're pioneering our understanding of E. coli's resilience.",
            "But our work is not finished yet. I have one more environmental challenge for you:",
            "can we find a replacement for glucose as E. coli's energy source?"
        ]

        self.m01_step4 = [
            "Did you already choose the best substitute for glucose?",
            "If you have your results, show them to me."
        ]

        self.m01_step5 = [
            f"Excellent work, {self.player.player_name}!",
            "You now understand how E. coli responds to oxygen and different carbon sources.",
            "Your discoveries will shape our research."
        ]
                

        self.input()
        if '01' in self.missions_completed and '02' in self.missions_completed:
            self.menu_message(self.m01_step5, buttons=False)

        elif '01' in self.missions_completed and '02' in self.missions_activated:
            self.menu_message(self.m01_step4, target_mission='02')

        elif '01' in self.missions_completed:
            self.menu_message(self.m01_step3, target_mission='02')

        elif '01' in self.missions_activated:
            self.menu_message(self.m01_step2)

        else:
            self.menu_message(self.m01_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()


   # def menu_message(self, message, buttons = True):
    def menu_message(self, message, buttons=True, target_mission='01'):

        menu_border = pygame.draw.rect(self.screen, (255,215,0), [0,500,1280,220], width=5)
        menu_bg = pygame.draw.rect(self.screen, (186,214,177), [5,505,1270,210])

        # pygame.display.set_caption('Cientista')
        imagem_path = get_resource_path('graphics/dialogues/martinez.jpg')
        imagem = get_dialogue_portrait(imagem_path)
        
        x = 25; # x coordnate of image
        y = 520; # y coordinate of image
        self.screen.blit(imagem, ( x,y))

        cientista_rect = pygame.draw.rect(self.screen, 'white', [25,675,150,25])

        nome = get_dialogue_text_surface(self.font_nome, 'Dr. Martinez')
        self.screen.blit(nome,(40,677))

        for line, msg in enumerate(message):
            msg = prepare_dialogue_text(msg, self.player.player_name)
            surf = get_dialogue_text_surface(self.font, msg)
            self.screen.blit(surf,(200,525+(line*20)+(15*line)))

        if buttons:
            def click_yes():
                if target_mission == '02':
                    mission02_menu = Mission02_info(self.toggle_menu, self.player)
                    self.pending = mission02_menu.update
                else:
                    self.pending = self.menu.update

            botao_teste = Button(200,650,150,50,self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370,650,220,50,self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()




class Mission_info:
    def __init__(self, toggle_menu, player) -> None:

        # general setup
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path,30)
        
        self.index = 0
        self.timer = Timer(200)

        self.mission01 = (
            '01' in self.missions_activated
            or '01' in self.missions_completed
        )

        #sounds
        success_path = get_resource_path('audio/success_3.ogg')
        self.success = pygame.mixer.Sound(success_path)
        self.success.set_volume(1.2)

        failed_path = get_resource_path('audio/failed.ogg')
        self.failed = pygame.mixer.Sound(failed_path)
        self.failed.set_volume(1.2)


    async def setup(self):

        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 01',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 01 Briefing',
            width=1280
        )


        menu_text.add.label(
            "\n"
            "Flux Balance Analysis (FBA) predicts feasible metabolic behaviour under a defined objective and a set of reaction bounds.\n\n"
            "Run a controlled comparison. First, use FBA with the biomass objective, no gene knockouts and the unchanged default environment. This is the aerobic baseline.\n\n"
            "Then run the same setup again and change only the lower bound of EX_o2_e from open to closed. Do not change any other environmental bound.\n\n"
            "Open Compare Runs and the Exchange Flux Report. A correct result shows that oxygen uptake becomes zero, E. coli still has positive growth, and anaerobic growth is lower than aerobic growth. Uptake is displayed as a positive magnitude, while its raw exchange flux is negative during consumption.\n\n"
            "The mission validates this relationship; it does not expect one exact rounded growth value or one unique byproduct profile, because FBA can have alternative optimal flux distributions."
            ,
            max_char=33,
            wordwrap=True
        )
        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)
        
        menu.add.label('Welcome, Lab Hero! \nYour journey begins with Mission 01: Into the Microbial World.\n'
            ,wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34)
        
        menu.add.label(
            "Dr. Martinez wants a controlled comparison between normal aerobic growth and growth without oxygen.\n"
            "Run the default FBA/biomass setup first. Then close only the lower bound of EX_o2_e and run it again.\n"
            "Use Compare Runs to verify that oxygen uptake is zero, growth remains positive, and growth decreases under anaerobic conditions.",
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30)
        menu.add.button('Mission 01 Briefing', menu_text, font_color = 'black',background_color=(255,215,0, 255))
        menu.add.vertical_margin(50)  
        if self.mission01:
              menu.add.button('Deliver Results', action=self.deliver_results, background_color=(50,100,100)) ## TASK: ADICIONAR FUNÇÃO ENTREGAR RESULTADOS
              menu.add.vertical_margin(50)
              menu.add.label('Mission Activated', font_color=(150, 150, 150))
              menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission01, background_color=(50,100,100))        
        menu.add.vertical_margin(20)

        await run_menu(menu, self.display_surface)



    def toggle_menu(self): 
        self.toggle_talk = not self.toggle_talk


    def activate_mission01(self):
        # Activation is idempotent. Reopening or calling the action twice must
        # not erase an in-progress or already validated comparison.
        if '01' in self.missions_completed:
            self.mission01 = True
            animation_text_save('Mission 01 is already completed.', time=2500)
            return
        if '01' in self.missions_activated:
            self.mission01 = True
            animation_text_save('Mission 01 is already active.', time=2500)
            return

        clear_compare_runs()
        clear_mission01_comparison_check()
        self.mission01 = True
        self.missions_activated.insert(0, '01')
        animation_text_save('Mission 01 Activated')
        save_file(self.player.get_save_data())


    def deliver_results(self):
        if '01' not in self.missions_activated:
            self.failed.play()
            animation_text_save('Activate Mission 01 before delivering results.', time=3000)
            return

        report_data = load_mission01_comparison_check()

        if (not report_data
                or report_data.get('mission_id') != '01'
                or report_data.get('check_version') != 2):
            self.failed.play()
            animation_text_save('Run the aerobic and anaerobic comparison first!', time=3000)
            return

        if report_data.get('ready_to_deliver'):
            self.success.play()
            if '01' not in self.missions_completed:
                self.missions_completed.insert(0, '01')
            animation_text_save('Congratulations! Mission 01 completed!', time=2500)
            save_file(self.player.get_save_data())
            return

        self.failed.play()
        if not report_data.get('baseline_run_found'):
            animation_text_save('Missing baseline: run default FBA with biomass objective first.', time=3200)
        elif not report_data.get('anaerobic_run_found'):
            animation_text_save('Close only the lower bound of EX_o2_e and run again.', time=3200)
        elif not report_data.get('anaerobic_growth_viable'):
            animation_text_save('The anaerobic run must still show positive viable growth.', time=3000)
        elif not report_data.get('growth_decreased'):
            animation_text_save('Anaerobic growth must be lower than the aerobic baseline.', time=3000)
        elif not report_data.get('anaerobic_oxygen_blocked'):
            animation_text_save('EX_o2_e uptake is not zero. Check the oxygen lower bound.', time=3000)
        else:
            animation_text_save('Open Compare Runs and check the controlled comparison.', time=3000)


    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback
            

    async def update(self):
        self.input()
        await self.setup()
        