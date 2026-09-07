import pygame
import pygame_menu
from settings import *
from options_values import mytheme
from timers import Timer
from async_menu import run_menu
from utils import get_resource_path


class YeastMicroscope:
    """Microscope viewer for the Golden Lab yeast areas."""

    def __init__(self, toggle_menu) -> None:
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        self.timer = Timer(200)

    async def setup(self):
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='S. cerevisiae',
            width=1280,
        )

        menu.add.label(
            'S. cerevisiae',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=50,
            font_color=(70, 70, 70),
        )

        yeast_path = get_resource_path('graphics/environment/Yeast.png')
        menu.add.image(yeast_path, scale=(1, 1))

        await run_menu(menu, self.display_surface)

    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()
        if keys[pygame.K_ESCAPE]:
            self.toggle_menu()

    async def update(self):
        self.input()
        await self.setup()
