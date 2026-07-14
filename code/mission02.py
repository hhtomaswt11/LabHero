import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from functions import animation_text_save
from button import Button
from async_menu import run_menu


class Mission02: 
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




        self.menu = Mission02_info(self.toggle_menu, self.player)
        self.pending = None


    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):

        self.m02_step1 = [
            "I'm Dr. Carter! I'm studying how E. coli behaves when its usual carbon source is unavailable.",
            "I prepared a set of possible alternative nutrients for you to compare.",
            "Can you find which one supports growth best?"
        ]
        
        self.m02_step2 = ["Have you compared the candidate carbon sources?",
                          "Show me the evidence behind your choice."]

        self.m02_step3 = [f"Excellent work, {self.player.player_name}!",
                          " ",
                          "You showed that nutrient availability can redirect microbial growth.",
                          "Choosing the right carbon source matters in biotechnology and environmental applications."
                          ]

        self.input()

        if '02' in self.missions_completed:
            self.menu_message(self.m02_step3, buttons=False)

        elif '02' in self.missions_activated:
            self.menu_message(self.m02_step2)

        else:
            self.menu_message(self.m02_step1)

        if self.pending is not None:
            coro_factory = self.pending
            self.pending = None
            await coro_factory()


    def menu_message(self, message, buttons = True):

        menu_border = pygame.draw.rect(self.screen, (255,215,0), [0,500,1280,220], width=5)
        menu_bg = pygame.draw.rect(self.screen, (186,214,177), [5,505,1270,210])

        # pygame.display.set_caption('Cientista')
        imagem_path = get_resource_path('graphics/dialogues/carter.jpg')
        imagem = pygame.image.load(imagem_path).convert()
        
        x = 25; # x coordnate of image
        y = 520; # y coordinate of image
        self.screen.blit(imagem, ( x,y))

        cientista_rect = pygame.draw.rect(self.screen, 'white', [25,675,150,25])

        nome = self.font_nome.render('Dr. Carter', True, 'black')
        self.screen.blit(nome,(55,677))

        for line, msg in enumerate(message):
            surf = self.font.render(msg, True, 'black')
            self.screen.blit(surf,(200,525+(line*20)+(15*line)))

        if buttons:
            def click_yes():
                self.pending = self.menu.update
            botao_teste = Button(200,650,150,50,self.screen, 'Yes', click_yes)
            botao_teste_2 = Button(370,650,220,50,self.screen, 'Not now', self.toggle_menu)
            botao_teste.process()
            botao_teste_2.process()

        pygame.display.flip()




class Mission02_info:
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

        if '02' in self.missions_activated:
            self.mission02 = True
        else:
            self.mission02 = False

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
            title='Mission 02',
            width=1280,
        )

        menu_text = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Mission 02 Briefing',
            width=1280
        )

        menu_text.add.label(
            """
            Carbon sources are nutrients that cells can use to obtain material and energy.

            Glucose usually supports strong E. coli growth, but metabolic models can help compare how the cell behaves when other carbon sources are available instead.

            In this mission, use the candidate list as your search space. Compare the growth response for each alternative under equivalent conditions and use the results to justify your choice.

            Do not look for a gene solution here. This is a nutrient-availability challenge.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0)
        )
        menu_text.add.label(
            """Concepts to observe:""",
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(100, 0),
            background_color = 'gold',
            font_color = 'black',
            font_size = 30,
            padding = (25,25,25,25)
        )
        menu_text.add.label(
            """
            - Nutrient availability can change microbial growth.

            - Exchange reactions represent how compounds enter or leave the model.

            - A fair comparison tests one alternative at a time.

            - Biomass/growth helps you compare which condition better supports E. coli.

            The correct answer should come from repeated simulations and result interpretation, not from guessing.
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0)
        )

        
        menu_text.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_text.add.vertical_margin(20)

        menu.add.vertical_margin(20)  
        menu.add.label("""Mission 02: Find a suitable substitute for glucose."""
            ,wordwrap=False,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=34)

        menu.add.label(
            """
            E. coli normally grows well with glucose. Your challenge is to compare possible alternative carbon sources and identify which one best supports growth.

            Candidate carbon sources:

            - malate                             - lactate
            - glutamate                        - glutamine
            - fumarate                         - fructose
            - ethanol                            - 2-oxoglutarate
            - acetaldehyde                    - acetate

            Use simulations to compare the candidates. The best answer should be supported by the growth result.
            """,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=30)
        
        menu.add.button('Mission 02 Briefing', menu_text, font_color = 'black',background_color=(255,215,0, 255))
        menu.add.vertical_margin(50)  
        if self.mission02:
            menu.add.text_input('Substitute: ', default='', input_underline='_', maxchar=14, onreturn=self.deliver_results)
            menu.add.vertical_margin(50)
            menu.add.label('Mission Activated', font_color=(150, 150, 150))
            menu.add.vertical_margin(20)
        else:
            menu.add.button('Activate Mission', action=self.activate_mission02, background_color=(50,100,100))        
        menu.add.vertical_margin(20)

        await run_menu(menu, self.display_surface)



    def toggle_menu(self):
        self.toggle_talk = not self.toggle_talk

    def activate_mission02(self):
        self.mission02 = True
        self.missions_activated.insert(0, '02')
        animation_text_save('Mission 02 Activated')


    def deliver_results(self, ans):
        # print(ans)
        right = self.check_results(ans)

        if right:
            self.success.play()
            self.missions_completed.insert(0, '02')
            animation_text_save('Congratulations! Mission Completed!', time=2000)
        else:
            self.failed.play()
            animation_text_save('No ... Try again!', time=2000)


    def check_results(self, ans):
        if ans == 'fructose':
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
        