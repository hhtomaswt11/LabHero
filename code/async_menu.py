import asyncio
import sys

import pygame
import pygame_menu

from functions import drain_animations


async def run_menu(menu, surface, on_update=None):
    """Async replacement for pygame_menu.Menu.mainloop.

    Yields to the event loop every frame so pygbag/wasm can pump browser events.
    Drains any queued animation_text_save overlays between menu update and next frame.
    on_update: optional callable invoked each frame before menu.update (e.g. ESC handling).
    """
    while menu.is_enabled():
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if on_update is not None:
            on_update()

        if menu.is_enabled():
            menu.update(events)

        # pygame-menu 4.4.x may still translate a ScrollArea horizontally from
        # mouse/touch dragging even when Menu overflow_x is disabled. Mission
        # screens are designed as a fixed-width 1280 px panel, so allowing that
        # translation exposes the grey surface outside the menu in Web builds.
        # Clamp mission-family menus to the left edge every frame while keeping
        # vertical scrolling fully available.
        if menu.is_enabled():
            try:
                title = str(menu.get_title())
            except Exception:
                title = ''
            if title.startswith('Mission '):
                try:
                    menu.get_scrollarea().scroll_to(
                        pygame_menu.locals.ORIENTATION_HORIZONTAL,
                        0,
                    )
                except (AttributeError, AssertionError, ValueError):
                    pass

        if menu.is_enabled():
            menu.draw(surface)

        pygame.display.update()
        await drain_animations()
        await asyncio.sleep(0)
