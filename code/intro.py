import sys

import pygame
from settings import *
import pygame_menu
from options_values import *
from button import Button
from utils import *
from async_menu import run_menu
from controls_content import populate_controls_menu


class Intro:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 130)
        self.font_text = pygame.font.Font(font_path, 30)
        self.width = 400
        self.space = 10
        self.padding = 8
        self.controls = Tutorial()
        self.story = Story()
        self.pending = None

        # These labels never change while an Intro instance is alive. Build
        # their surfaces/geometry once instead of rasterizing the same text
        # on every frame of the intro loop.
        self.title = self.font.render('LabHero', False, 'black')
        self.title_rect = self.title.get_rect(
            center=(SCREEN_WIDTH/2, (SCREEN_HEIGHT/2)-100))

        # Desktop and Web expose the same two title-screen actions.  In the
        # browser ENTER resumes the durable localStorage save while SPACE
        # explicitly starts a fresh campaign, so both choices must be visible.
        self.text = self.font_text.render(
            'press ENTER to continue', False, 'red')
        self.text2 = self.font_text.render(
            'or press SPACE to new game', False, (60, 150, 140))
        self.text_rect = self.text.get_rect(
            center=(SCREEN_WIDTH/2, (SCREEN_HEIGHT/2)))
        self.text_rect2 = self.text2.get_rect(
            center=(SCREEN_WIDTH/2, (SCREEN_HEIGHT/2)+40))

        # Starting a fresh campaign is destructive because it clears the
        # student's durable save.  Cache the confirmation surfaces here so the
        # title screen still does no font rendering in its per-frame run loop.
        self.new_game_confirmation_pending = False
        self.confirm_title = self.font_text.render(
            'Start a new game?', False, 'black')
        self.confirm_warning = self.font_text.render(
            'This will erase your current saved progress.', False, (150, 40, 40))
        self.confirm_action = self.font_text.render(
            'Press SPACE again to confirm.', False, 'black')
        self.confirm_back = self.font_text.render(
            'Press ESC to go back.', False, (60, 80, 80))
        self.confirm_title_rect = self.confirm_title.get_rect(
            center=(SCREEN_WIDTH/2, 345))
        self.confirm_warning_rect = self.confirm_warning.get_rect(
            center=(SCREEN_WIDTH/2, 390))
        self.confirm_action_rect = self.confirm_action.get_rect(
            center=(SCREEN_WIDTH/2, 440))
        self.confirm_back_rect = self.confirm_back.get_rect(
            center=(SCREEN_WIDTH/2, 480))

    def request_new_game_confirmation(self):
        self.new_game_confirmation_pending = True

    def cancel_new_game_confirmation(self):
        self.new_game_confirmation_pending = False

    def run(self):

        self.display_surface.fill('gold')
        self.display_surface.blit(self.title, self.title_rect)
        self.display_surface.blit(self.text, self.text_rect)
        if self.text2 is not None:
            self.display_surface.blit(self.text2, self.text_rect2)

        if self.new_game_confirmation_pending:
            # Overlay a centred confirmation card and suppress the title-screen
            # buttons until the player confirms or cancels.  A second SPACE is
            # therefore required before any save data can be deleted.
            panel = (190, 310, 900, 215)
            pygame.draw.rect(self.display_surface, 'white', panel, border_radius=10)
            pygame.draw.rect(
                self.display_surface, 'black', panel, width=3, border_radius=10)
            self.display_surface.blit(self.confirm_title, self.confirm_title_rect)
            self.display_surface.blit(self.confirm_warning, self.confirm_warning_rect)
            self.display_surface.blit(self.confirm_action, self.confirm_action_rect)
            self.display_surface.blit(self.confirm_back, self.confirm_back_rect)
            return
        # botao_continue = Button(
        #     240, 450, 250, 50, self.display_surface, 'Continue Game', self.continue_game)
        # botao_new = Button(515, 450, 250, 50,
        #                    self.display_surface, 'New Game', self.new_game)
        # botao_tutorial = Button(
        #     790, 500, 250, 50, self.display_surface, 'Tutorial', self.tutorial.update)
        # botao_continue.process()
        # botao_new.process()
        

        def show_tutorial():
            self.pending = self.controls.update

        def show_story():
            self.pending = self.story.update

        botao_tutorial = Button(
            515, 450, 250, 50, self.display_surface, 'Controls', show_tutorial, bg_color= 'black', font_color='white')
        botao_tutorial.process()

        botao_story = Button(
            515, 510, 250, 50, self.display_surface, 'Story', show_story)
        botao_story.process()



class Tutorial:
    def __init__(self) -> None:

        # genereal setup
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)


    async def setup(self):

        menu_how_to_play = pygame_menu.Menu('How to Play', 1280, 720,
                                            onclose=pygame_menu.events.BACK,
                                            theme=tutorial_theme)

        populate_controls_menu(
            menu_how_to_play,
            is_web=(sys.platform == 'emscripten'),
        )

        await run_menu(menu_how_to_play, self.display_surface)

    def input(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback

    async def update(self):
        self.input()
        await self.setup()


class Story:
    def __init__(self) -> None:

        # genereal setup
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)


    async def setup(self):

        menu_story = pygame_menu.Menu('LabHero Story', 1280, 720,
                                            onclose=pygame_menu.events.BACK,
                                            theme=tutorial_theme)
        menu_story.add.label(
            """
            You are a student entering the LabHero systems-biology laboratory.

            Start by registering with Dr. Melo. You will then follow either the full Normal campaign or the shorter curated Easy campaign.

            Across the laboratories, researchers will give you missions in constraint-based metabolic modelling. Talk to them, understand the biological question and use the simulator to build controlled environmental and genetic experiments.

            Your conclusions must be supported by the visible simulation evidence. The library, hints and reports are available whenever you need to revisit a concept or inspect a result more carefully.

            Explore the laboratories, learn from each researcher and apply the same modelling discipline as the challenges become more complex.

            Welcome to LabHero!
            """,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
            padding = (50,50)
        )
        
        await run_menu(menu_story, self.display_surface)

    def input(self):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback

    async def update(self):
        self.input()
        await self.setup()
