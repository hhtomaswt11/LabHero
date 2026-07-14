import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from button import Button
from async_menu import run_menu
from mission04 import Mission04_info
from mission05 import Mission05_info


class Mission03: 
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


        self.menu = Mission03_info(self.toggle_menu, self.player)
        self.pending = None


    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):

        self.m03_step1 = [
            f"Greetings {self.player.player_name}! I'm Dr. Silva.",
            "I have a small set of candidate genes from E. coli.",
            "One of them seems critical for survival. Can you identify which one?"
        ]
        
        self.m03_step2 = [
            "Have you tested the candidate knockouts?",
            "Show me what the growth results revealed."
        ]

        self.m03_step3 = [
            "Very good! You learned how a knockout can reveal an essential gene.",
            "But knockouts are not only used to test survival.",
            "They can also redirect metabolism toward useful products. Let's go further."
        ]

        self.m03_step4 = [
            "Did you already test the production knockout?",
            "Keep the environmental conditions unchanged.",
            "Focus only on the genetic change."
        ]

        self.m03_step5 = [
            "Excellent! You redirected metabolism in aerobic conditions.",
            "Now let's combine a knockout with an environmental change.",
            "What can E. coli produce without oxygen?"
        ]

        self.m03_step6 = [
            "Did you manage to combine both variables?",
            "Let me see what you got."
        ]

        self.m03_step7 = [
            f"Excellent work, {self.player.player_name}!",
            "You now understand essential genes, production knockouts,",
            "and how environment can change metabolic engineering strategies."
        ]

        self.input()
        if '03' in self.missions_completed and '04' in self.missions_completed and '05' in self.missions_completed:
            self.menu_message(self.m03_step7, buttons=False)

        elif '03' in self.missions_completed and '04' in self.missions_completed and '05' in self.missions_activated:
            self.menu_message(self.m03_step6, target_mission='05')

        elif '03' in self.missions_completed and '04' in self.missions_completed:
            self.menu_message(self.m03_step5, target_mission='05')

        elif '03' in self.missions_completed and '04' in self.missions_activated:
            self.menu_message(self.m03_step4, target_mission='04')

        elif '03' in self.missions_completed:
            self.menu_message(self.m03_step3, target_mission='04')

        elif '03' in self.missions_activated:
            self.menu_message(self.m03_step2)

        else:
            self.menu_message(self.m03_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()


    def menu_message(self, message, buttons=True, target_mission='03'):

        menu_border = pygame.draw.rect(self.screen, (255,215,0), [0,500,1280,220], width=5)
        menu_bg = pygame.draw.rect(self.screen, (186,214,177), [5,505,1270,210])

        # pygame.display.set_caption('Cientista')
        imagem_path = get_resource_path('graphics/dialogues/silva.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        
        x = 25; # x coordnate of image
        y = 520; # y coordinate of image
        self.screen.blit(imagem, ( x,y))

        cientista_rect = pygame.draw.rect(self.screen, 'white', [25,675,150,25])

        nome = self.font_nome.render('Dr. Silva', True, 'black')
        self.screen.blit(nome,(55,677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf,(200,525+(line*20)+(15*line)))

        if buttons:
            def click_yes():
                if target_mission == '04':
                    mission04_menu = Mission04_info(self.toggle_menu, self.player)
                    self.pending = mission04_menu.update
                elif target_mission == '05':
                    mission05_menu = Mission05_info(self.toggle_menu, self.player)
                    self.pending = mission05_menu.update
                else:
                    self.pending = self.menu.update

            botao_teste = Button(200,650,150,50,self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370,650,220,50,self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()




class Mission03_info:
    def __init__(self, toggle_menu, player) -> None:

        # general setup
        self.player = player
        self.missions_activated = self.player.missions_activated
        self.missions_completed = self.player.missions_completed

        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)
        
        self.index = 0
        self.timer = Timer(200)

        if '03' in self.missions_activated:
            self.mission03 = True
        else:
            self.mission03 = False

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
            title='Mission 03',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 03 Briefing',
            width=1280
        )

        menu_text.add.label(
            """
            An essential gene is a gene that the organism needs to maintain a viable metabolic state.
            If that gene is removed, the model may lose the ability to support normal growth.

            Gene knockout simulations are used to test this idea computationally: instead of changing
            the environment, the model is perturbed genetically and the growth response is observed.

            Use the candidate list as the search space and compare the growth behaviour after each
            genetic perturbation. The strongest loss of viability is the key evidence.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0)
        )

        
        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)

        menu.add.label("Mission 03 - Genetic Mystery"
            ,wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34)
        
        menu.add.label(
            """
            Dr. Silva suspects that one candidate gene is essential for E. coli survival.

            Candidate genes:
            b1241  b3115  b3736  b2975  b1524  b2278  b2926  b2297  b0728  b3919

            Test the candidates through knockout simulations and compare the growth results.
            The candidate genes will appear highlighted in the simulation menu.

            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30)
        menu.add.button('Mission 03 Briefing', menu_text, font_color = 'black',background_color=(255,215,0, 255))
        menu.add.vertical_margin(50)  
        if self.mission03:
            menu.add.text_input('Essential Gene: ', default='', input_underline='_', maxchar=5, onreturn=self.deliver_results)
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission03, background_color=(50,100,100))        
        menu.add.vertical_margin(20)

        await run_menu(menu, self.display_surface)



    def toggle_menu(self):
        self.toggle_talk = not self.toggle_talk

    def activate_mission03(self):
        self.mission03 = True
        self.missions_activated.insert(0, '03')
        animation_text_save('Mission 03 Activated')


    def deliver_results(self, ans):
        # print(ans)
        right = self.check_results(ans)

        if right:
            self.success.play()
            self.missions_completed.insert(0, '03')
            animation_text_save('Congratulations! Mission Completed!', time=2000)
        else:
            self.failed.play()
            animation_text_save('No ... Try again!', time=2000)


    def check_results(self, ans):
        if ans == 'b2926':
            return True
        else:
            return False



    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback
            

    async def update(self):
        self.input()
        await self.setup()
        