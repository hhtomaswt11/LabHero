import pygame_menu

from book_content import BOOK_BY_ID


def populate_book_menu(menu, book_id, *, back_action=pygame_menu.events.BACK):
    """Populate a pygame-menu screen from the canonical BOOKS.1 content.

    ``back_action`` is configurable because a book opened from the library is
    run as its own top-level async menu, while the Settings How to Play screen
    is a normal pygame-menu submenu.
    """
    book = BOOK_BY_ID[book_id]

    menu.add.label(
        book['intro'],
        max_char=-1,
        wordwrap=True,
        align=pygame_menu.locals.ALIGN_LEFT,
        margin=(0, 0),
    )
    menu.add.vertical_margin(20)

    for section_title, paragraphs in book['sections']:
        menu.add.label(
            section_title,
            max_char=-1,
            wordwrap=True,
            align=pygame_menu.locals.ALIGN_LEFT,
            margin=(0, 0),
            background_color='white',
            font_color='darkgreen',
            font_size=35,
        )
        for paragraph in paragraphs:
            menu.add.label(
                paragraph,
                max_char=-1,
                wordwrap=True,
                align=pygame_menu.locals.ALIGN_LEFT,
                margin=(0, 0),
            )
        menu.add.vertical_margin(15)

    menu.add.button(
        'Back',
        back_action,
        background_color=(70, 70, 70),
    )
    menu.add.vertical_margin(50)
    return menu
