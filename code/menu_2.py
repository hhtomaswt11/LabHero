import sys

import pygame
import pygame_menu
from settings import *
from level import *
from options_values import *
from save_load import *
from timers import Timer
from functions import animation_text_save
from utils import *
from async_menu import run_menu
from book_ui import populate_book_menu


class Menu:
    def __init__(self, player, toggle_menu) -> None:

        # genereal setup
        self.toggle_menu = toggle_menu
        self.player = player
        self.display_surface = pygame.display.get_surface()
        self.font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(self.font_path, 30)

        # self.setup()

        # movement
        self.index = 0
        self.timer = Timer(200)

        # Music state mirrors the actual Player startup volume.
        self.volume = DEFAULT_MUSIC_VOLUME_PERCENT / 100.0
        self.music_val = 0



    def save_game(self, menu=None):
        # Student identity is registered once through Dr. Alves and is not
        # editable from Settings during the campaign.
        save_file(self.player.get_save_data())
        animation_text_save('Game saved')

    def back_to_spawnpoint(self, menu):
        """Teleport to the canonical map Start point and persist it."""
        if not self.player.return_to_spawnpoint():
            animation_text_save('Spawnpoint is not available.', time=1800)
            return

        # Persist immediately so browser autosave/refresh cannot restore the
        # pre-teleport position. No mission, reward or profile data is reset.
        save_file(self.player.get_save_data())
        animation_text_save('Returned to spawnpoint.', time=1800)

        # Close Settings so the player immediately sees the destination.
        self.toggle_menu()
        menu.disable()
    


    async def setup(self):
        menu = pygame_menu.Menu('LabHero Settings', 1280, 720,
                        onclose=self.toggle_menu,
                        theme=mytheme)
        
        menu_how_to_play = pygame_menu.Menu(
            'How to Play',
            1280,
            720,
            onclose=self.toggle_menu,
            theme=mytheme,
            column_max_width=1280,
        )
        
        menu_credits = pygame_menu.Menu('Credits', 1280, 720,
                        onclose=self.toggle_menu,
                        theme=mytheme)
        
        # menu_credits.add.label(
        #     """
        #     Font Lychee Soda by jeti {https://fontenddev.com/fonts/lychee-soda/}{link}
        #     Music by 
        #     """,
        #     max_char=-1,
        #     wordwrap=True,
        #     align=pygame_menu.locals.ALIGN_CENTER,
        #     margin=(0, 0)
        # )
        menu_credits.add.vertical_margin(50)
        menu_credits.add.url('https://fontenddev.com/fonts/lychee-soda/', 'Font Lychee Soda by jeti', font_color='firebrick')
        menu_credits.add.vertical_margin(20)
        menu_credits.add.url('https://dafonttop.com/munro.font', 'Font Munro by Ed Merrit', font_color='firebrick')
        menu_credits.add.vertical_margin(20)
        menu_credits.add.url('https://www.FesliyanStudios.com', 'Royalty free music from https://www.FesliyanStudios.com', font_color=(110,175,221))
        menu_credits.add.vertical_margin(20)
        menu_credits.add.url('https://cupnooble.itch.io/', 'Asset Pack by Cup Nooble', font_color=(84,145,76))
        menu_credits.add.vertical_margin(20)
        # menu_credits.add.url('', 'Assets by João Leiras and Gabriela Barbosa', font_color='black')
        menu_credits.add.label('Assets by Joao Leiras and Gabriela Barbosa', font_color='black')
        menu_credits.add.vertical_margin(20)
        menu_credits.add.label('Game developed by Monica Leiras and Tomas Melo', font_color='black')
        # menu_credits.add.url('', 'Game developed by Mónica Leiras', font_color='black')
        menu_credits.add.vertical_margin(50)
        menu_credits.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_credits.add.vertical_margin(50)
        


        
        
        # Use the same canonical How to Play content as the library.
        populate_book_menu(menu_how_to_play, 'how_to_play')

        student_label = self.player.player_name if self.player.name_confirmed else 'Not registered'
        # pygame-menu's bundled Munro font does not contain common accented
        # Portuguese glyphs (á, ã, ç, ...).  Use the same Unicode-capable
        # LycheeSoda font already used by LabHero dialogues for this
        # player-controlled Unicode label.
        menu.add.label(
            f'Student: {student_label}',
            font_name=self.font_path,
        )
        menu.add.label(f'Mode: {self.player.campaign_mode.title()}')
        menu.add.selector('Music: ', [('Hope', 0), ('Serene', 1),  ('Happy', 2), ('Surf', 3)], default=self.music_val, onchange=self.set_music)
        menu.add.range_slider('Volume', self.volume*100, (0, 100), 1, onchange=self.set_volume,
                      rangeslider_id='volume_music',
                      value_format=lambda x: str(int(x)))
        menu.add.button('Back to Spawnpoint', self.back_to_spawnpoint, menu)
        menu.add.button('How to Play', action=menu_how_to_play)
        if sys.platform != 'emscripten':
            menu.add.button('Save Game', self.save_game, menu)
        menu.add.button('Credits', action=menu_credits)

        if sys.platform == 'emscripten':
            def back_to_title():
                # Preserve durable browser progress when returning to the title.
                # Only the hot RAM cache is cleared; Continue reloads localStorage.
                save_file(self.player.get_save_data())
                clear_memstore()
                self.player.restart_to_intro = True
                self.toggle_menu()
                menu.disable()
            menu.add.button('Back to Title', back_to_title)
        else:
            def save_and_quit():
                self.save_game(menu)
                pygame.quit()
                sys.exit()
            menu.add.button('Quit Game', save_and_quit)

        await run_menu(menu, self.display_surface)

    

    def toggle_menu(self):
        self.toggle_shop = not self.toggle_shop

    def set_music(self, value, extra):
        MUSIC_NAME = value[0][0] # name of music
        self.music_val = value[1] # int value
        self.player.music_bg = pygame.mixer.stop()
        self.player.music_bg = pygame.mixer.Sound(MUSIC[value[0][0]])
        self.player.music_bg.set_volume(self.volume*0.14)
        self.player.music_bg.play(loops = -1)


    def set_volume(self, value):
        self.volume = (value/100)
        self.player.music_bg.set_volume(self.volume*0.14)
        # print(self.volume)
        

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback
            

    async def update(self):
        self.input()
        await self.setup()
        

