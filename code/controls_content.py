import pygame_menu


SECTION_STYLE = {
    "max_char": -1,
    "wordwrap": True,
    "align": pygame_menu.locals.ALIGN_LEFT,
    "margin": (100, 0),
    "background_color": (60, 150, 140),
    "font_color": "white",
    "font_size": 30,
    "padding": (25, 25, 25, 25),
}

BODY_STYLE = {
    "max_char": -1,
    "wordwrap": True,
    "align": pygame_menu.locals.ALIGN_LEFT,
    "margin": (0, 0),
}


def _sections(is_web=False):
    main_menu = (
        "Press M to open Settings. Back to Spawnpoint returns you to the map's initial "
        "Start position without resetting progress. In the browser, progress is saved automatically "
        "and Back to Title returns safely to the title screen. On desktop, "
        "Settings also provides Save Game and Quit Game."
        if is_web
        else
        "Press M to open Settings, where you can change music/volume, use Back to "
        "Spawnpoint to return to the map's initial Start position without resetting "
        "progress, review these controls, save the game and quit."
    )

    return (
        (
            "Title Screen",
            "Press ENTER to continue the current save. Press SPACE to start a New Game, then press SPACE again to confirm or ESC to cancel.",
        ),
        (
            "Movement",
            "Move with the arrow keys or WASD.",
        ),
        (
            "Interaction",
            "Press ENTER when close to a scientist, Dr. Alves, a simulator desk, "
            "the library, an apple tree or the coffee machine. ESC closes/backtracks "
            "from dialogues and most menus.",
        ),
        (
            "Inventory",
            "Press E during exploration to open the Inventory. It shows your hint keys, "
            "current score and unlocked skins. Use Left/Right or A/D to change skin, "
            "ENTER to apply it, and E or ESC to close.",
        ),
        (
            "Menus",
            "Use the mouse to press dialogue and menu buttons. ENTER is also used to "
            "confirm actions in overlays such as the Inventory.",
        ),
        (
            "Main Menu",
            main_menu,
        ),
    )


def populate_controls_menu(menu, *, is_web=False, include_back=False):
    """Populate a pygame-menu screen with the current LabHero controls."""
    menu.add.vertical_margin(50)
    for title, body in _sections(is_web=is_web):
        menu.add.label(title, **SECTION_STYLE)
        menu.add.label(body, **BODY_STYLE)
        menu.add.vertical_margin(50)

    if include_back:
        menu.add.button(
            "Back",
            pygame_menu.events.BACK,
            background_color=(70, 70, 70),
        )
        menu.add.vertical_margin(50)
