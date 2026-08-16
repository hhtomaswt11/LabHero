import pygame
from utils import *


# Button instances can be short-lived (dialogue renderers currently recreate
# them every frame), but their visual assets are immutable for a given style.
# Cache only those immutable resources.  Interaction state such as
# ``alreadyPressed`` deliberately remains per Button instance so click
# semantics and dialogue lifecycle behaviour stay unchanged.
_BUTTON_FONT_CACHE = {}
_BUTTON_VISUAL_CACHE = {}


def _cache_key_part(value):
    """Return a stable, hashable representation for pygame colour inputs."""
    return repr(value)


def _get_button_font(font_path, size):
    key = (font_path, int(size))
    font = _BUTTON_FONT_CACHE.get(key)
    if font is None:
        font = pygame.font.Font(font_path, size)
        _BUTTON_FONT_CACHE[key] = font
    return font


def _get_button_visuals(width, height, button_text, bg_color, font_color, font_path, font_size=34):
    """Return cached immutable surfaces for normal/hover/pressed button states."""
    key = (
        int(width), int(height), str(button_text),
        _cache_key_part(bg_color), _cache_key_part(font_color),
        font_path, int(font_size),
    )
    cached = _BUTTON_VISUAL_CACHE.get(key)
    if cached is not None:
        return cached

    font = _get_button_font(font_path, font_size)
    text_surface = font.render(str(button_text), True, font_color)
    fill_colors = {
        'normal': bg_color,
        'hover': '#666666',
        'pressed': '#333333',
    }

    visuals = {}
    for state, fill_color in fill_colors.items():
        surface = pygame.Surface((width, height))
        surface.fill(fill_color)
        surface.blit(text_surface, [
            width / 2 - text_surface.get_rect().width / 2,
            height / 2 - text_surface.get_rect().height / 2,
        ])
        visuals[state] = surface

    cached = (font, text_surface, visuals)
    _BUTTON_VISUAL_CACHE[key] = cached
    return cached


def clear_button_resource_cache():
    """Clear cached immutable button assets (primarily useful for tests)."""
    _BUTTON_FONT_CACHE.clear()
    _BUTTON_VISUAL_CACHE.clear()


class Button():
    def __init__(self, x, y, width, height, screen, buttonText='Button', onclickFunction=None, onePress=False, bg_color = 'white', font_color = 'black'):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.screen = screen
        self.onclickFunction = onclickFunction
        self.onePress = onePress
        self.alreadyPressed = False

        self.fillColors = {
            'normal': bg_color,
            'hover': '#666666',
            'pressed': '#333333',
        }

        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font, self.buttonSurf, self._buttonVisuals = _get_button_visuals(
            self.width,
            self.height,
            buttonText,
            bg_color,
            font_color,
            font_path,
            34,
        )
        self.buttonSurface = self._buttonVisuals['normal']
        self.buttonRect = pygame.Rect(self.x, self.y, self.width, self.height)

        # objects.append(self)

    def process(self):
        mousePos = pygame.mouse.get_pos()
        visual_state = 'normal'
        if self.buttonRect.collidepoint(mousePos):
            visual_state = 'hover'
            if pygame.mouse.get_pressed(num_buttons=3)[0]:
                visual_state = 'pressed'
                if self.onePress:
                    self.onclickFunction()
                elif not self.alreadyPressed:
                    self.onclickFunction()
                    self.alreadyPressed = True
            else:
                self.alreadyPressed = False

        self.buttonSurface = self._buttonVisuals[visual_state]
        self.screen.blit(self.buttonSurface, self.buttonRect)





if __name__ == '__main__':
    import sys

    pygame.init()
    fps = 60
    fpsClock = pygame.time.Clock()
    width, height = 640, 480
    screen = pygame.display.set_mode((width, height))

    font = pygame.font.SysFont('Arial', 40)

    objects = []
        
    def myFunction():
        print('Button Pressed')


    botao = Button(30, 30, 400, 100, screen, onclickFunction=myFunction)
    # botao2 = Button(30, 30, 400, 100, screen)


    while True:
        screen.fill((20, 20, 20))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        botao.process()
        # botao2.process()

        pygame.display.flip()
        fpsClock.tick(fps)
