import pygame
import pygame_menu

from settings import *
from timers import Timer
from options_values import mytheme
from async_menu import run_menu
from book_content import BOOK_LIBRARY, BOOK_BY_ID
from book_ui import populate_book_menu


class Books:
    """Mission-aligned scientific reference library.

    BOOKS.1 keeps menu construction generic while the canonical text lives in
    ``book_content.py``.  The content module is intentionally pygame-free so
    it can be regression-tested without initializing the game runtime.
    """

    def __init__(self, toggle_menu) -> None:
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        font_path = get_resource_path('font/LycheeSoda.ttf')
        self.font = pygame.font.Font(font_path, 30)

        self.index = 0
        self.timer = Timer(200)

        self._pending_book = None
        self._top_menu = None

    def _on_book_click(self, book_id):
        def handler():
            self._pending_book = book_id
            if self._top_menu is not None:
                self._top_menu.disable()
        return handler

    def _build_top_menu(self):
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Books',
            width=1280,
        )
        menu.add.label(
            'Books Available:',
            align=pygame_menu.locals.ALIGN_CENTER,
            font_size=50,
            font_color=(70, 70, 70),
        )
        menu.add.vertical_margin(15)

        for book in BOOK_LIBRARY:
            menu.add.button(
                book['title'],
                self._on_book_click(book['id']),
                background_color=book['color'],
            )
        return menu

    def _build_book(self, book_id):
        book = BOOK_BY_ID[book_id]
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title=book['title'],
            width=1280,
            column_max_width=1280,
        )

        # Library books are run as independent async menus, not pygame-menu
        # child submenus.  BACK alone therefore has no parent to return to.
        # Disable this book menu explicitly so Books.update() can rebuild the
        # library index.
        populate_book_menu(menu, book_id, back_action=menu.disable)
        return menu

    async def update(self):
        while True:
            self._pending_book = None
            self._top_menu = self._build_top_menu()
            await run_menu(self._top_menu, self.display_surface)

            book_id = self._pending_book
            self._top_menu = None
            if book_id is None:
                return

            await run_menu(self._build_book(book_id), self.display_surface)
