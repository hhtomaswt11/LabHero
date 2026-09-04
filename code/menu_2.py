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
from teacher_mode import build_teacher_request, teacher_missions_for_mode


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

        def back_to_title():
            # Save into the currently active namespace. During Teacher Preview
            # that namespace is disposable and is cleared by Game afterwards;
            # normal Web progress remains durable for Continue.
            save_file(self.player.get_save_data())
            clear_memstore()
            self.player.teacher_switch_request = None
            self.player.restart_to_intro = True
            self.toggle_menu()
            menu.disable()

        if getattr(self.player, 'teacher_preview', False):
            # Mission switching uses a text input too. Re-arm Pygbag text input
            # because the previous Teacher auth/switch form deliberately stops
            # it before returning to the world.
            try:
                pygame.key.start_text_input()
            except Exception:
                pass

            teacher_switch = pygame_menu.Menu(
                'Change Teacher Mission',
                1280,
                720,
                onclose=pygame_menu.events.BACK,
                theme=mytheme,
            )
            teacher_switch.add.label(
                'Teacher session already authenticated. Switch preview without returning to the title screen.',
                max_char=-1,
                wordwrap=True,
                font_size=25,
            )
            teacher_switch.add.label(
                f'Current preview: {self.player.campaign_mode.title()} - Mission {self.player.teacher_target_mission}',
                max_char=-1,
                wordwrap=True,
                font_size=25,
            )
            teacher_switch.add.vertical_margin(15)
            teacher_mission_widget = teacher_switch.add.text_input(
                'Mission number: ',
                default=str(self.player.teacher_target_mission or '1'),
                maxchar=2,
                input_type=pygame_menu.locals.INPUT_INT,
                textinput_id='teacher_switch_mission',
            )
            teacher_switch_error = teacher_switch.add.label(
                '',
                max_char=-1,
                wordwrap=True,
                font_color='firebrick',
                font_size=23,
            )

            def switch_teacher_mission(mode):
                mission_value = teacher_mission_widget.get_value()
                request = build_teacher_request(
                    mission_value,
                    mode,
                    source='preview',
                )
                if request is None:
                    available = ', '.join(teacher_missions_for_mode(mode))
                    teacher_switch_error.set_title(
                        f'Mission {mission_value} is not part of the {mode.title()} route. '
                        f'Available missions: {available}.'
                    )
                    return

                # Signal the outer Game teacher-session loop. It will dispose of
                # this preview namespace and create a fresh isolated preview for
                # the requested mission without another credential prompt.
                self.player.teacher_switch_request = request
                self.player.restart_to_intro = True
                try:
                    pygame.key.stop_text_input()
                except Exception:
                    pass
                teacher_switch.disable()
                menu.disable()
                self.toggle_menu()

            teacher_switch.add.button(
                'Switch to Normal Mission',
                lambda: switch_teacher_mission('normal'),
            )
            teacher_switch.add.button(
                'Switch to Easy Mission',
                lambda: switch_teacher_mission('easy'),
            )
            teacher_switch.add.button(
                'Back',
                pygame_menu.events.BACK,
                background_color=(70, 70, 70),
            )

            # Teacher Preview must return cleanly to the title on both Web and
            # desktop instead of quitting or touching the student's namespace.
            menu.add.button('Change Teacher Mission', teacher_switch)
            menu.add.button('Exit Teacher Preview', back_to_title)
        elif sys.platform == 'emscripten':
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
        

