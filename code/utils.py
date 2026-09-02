import sys
import os

APP_NAME = 'LabHero'

# Optional persistence namespace used by isolated runtime sessions such as
# TEACHER.1. Normal gameplay keeps this unset and therefore preserves every
# historic save path exactly.
_SAVE_NAMESPACE = None


def set_save_namespace(namespace=None):
    global _SAVE_NAMESPACE
    value = str(namespace or '').strip()
    _SAVE_NAMESPACE = value or None


def get_save_namespace():
    return _SAVE_NAMESPACE


def get_resource_path(relative_path):
    """ Get the absolute path to a read-only resource bundled with the game."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_save_path(filename):
    """Return the absolute path for a user-writable save file.

    Saves live outside the bundle so they survive reinstall and work in
    PyInstaller --onefile builds, where the bundle dir is a temp folder.
    """
    if sys.platform == 'win32':
        base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), APP_NAME)
    elif sys.platform == 'darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', APP_NAME)
    else:
        xdg = os.environ.get('XDG_DATA_HOME')
        base = os.path.join(xdg, APP_NAME) if xdg else os.path.join(os.path.expanduser('~'), '.local', 'share', APP_NAME)
    namespace = get_save_namespace()
    if namespace:
        base = os.path.join(base, namespace)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, filename)

DIALOGUE_PLAYER_NAME_MAX_CHARS = 18

def compact_dialogue_player_name(name, max_chars=DIALOGUE_PLAYER_NAME_MAX_CHARS):
    """Return a display-only player name that cannot overflow dialogue lines.

    The full name remains unchanged in the player profile and save file. Only
    dialogue rendering uses this compact form.
    """
    value = ' '.join(str(name or '').split()) or 'Player'
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + '...'


def prepare_dialogue_text(message, player_name):
    """Replace a full player name in a dialogue line with its safe display form."""
    text = str(message)
    full_name = str(player_name or '')
    if not full_name or full_name not in text:
        return text
    return text.replace(full_name, compact_dialogue_player_name(full_name))

# Dialogue portraits are immutable UI assets.  Keep converted/resized surfaces
# in memory after first use so browser/WASM builds do not reopen the same JPEG
# from the virtual filesystem on every dialogue frame.
_DIALOGUE_PORTRAIT_BASE_CACHE = {}
_DIALOGUE_PORTRAIT_SCALED_CACHE = {}


def get_dialogue_portrait(image_path, size=None):
    """Return a cached display-converted dialogue portrait.

    ``menu_message`` methods run once per rendered frame while a dialogue is
    open.  Loading and converting the same portrait there repeatedly is wasted
    work, especially under Pygbag.  The base image is therefore loaded and
    converted once per path; an optional resized variant is cached separately.

    The pygame import stays local so utility-only/backend imports of this module
    do not gain a pygame dependency merely by importing ``utils``.
    """
    import pygame

    path = os.fspath(image_path)
    image = _DIALOGUE_PORTRAIT_BASE_CACHE.get(path)
    if image is None:
        image = pygame.image.load(path).convert()
        _DIALOGUE_PORTRAIT_BASE_CACHE[path] = image

    if size is None:
        return image

    target_size = tuple(size)
    if image.get_size() == target_size:
        return image

    key = (path, target_size)
    scaled = _DIALOGUE_PORTRAIT_SCALED_CACHE.get(key)
    if scaled is None:
        scaled = pygame.transform.smoothscale(image, target_size)
        _DIALOGUE_PORTRAIT_SCALED_CACHE[key] = scaled
    return scaled



# Dialogue text is also immutable for a given font/text/style combination.
# Cache rendered surfaces so per-frame dialogue drawing does not repeatedly
# rasterize the same name and message lines under Pygbag/WebAssembly.
_DIALOGUE_TEXT_SURFACE_CACHE = {}
_DIALOGUE_TEXT_FONT_REFS = {}


def get_dialogue_text_surface(font, text, antialias=True, color='black'):
    """Return a cached ``Font.render`` surface for dialogue UI text.

    Mission dialogue renderers run once per frame while a conversation is open.
    Names and prepared message lines are stable, so rasterizing them again on
    every frame is unnecessary work.  Keep a strong reference to the font for
    every cached ``id(font)`` so Python cannot recycle that id while entries
    remain in the cache.
    """
    font_id = id(font)
    _DIALOGUE_TEXT_FONT_REFS[font_id] = font
    rendered_text = str(text)
    key = (font_id, rendered_text, bool(antialias), repr(color))
    surface = _DIALOGUE_TEXT_SURFACE_CACHE.get(key)
    if surface is None:
        surface = font.render(rendered_text, antialias, color)
        _DIALOGUE_TEXT_SURFACE_CACHE[key] = surface
    return surface


def clear_dialogue_text_cache():
    """Clear cached dialogue text surfaces (primarily useful for tests)."""
    _DIALOGUE_TEXT_SURFACE_CACHE.clear()
    _DIALOGUE_TEXT_FONT_REFS.clear()

def clear_dialogue_portrait_cache():
    """Clear cached portrait surfaces (primarily useful for tests/display resets)."""
    _DIALOGUE_PORTRAIT_BASE_CACHE.clear()
    _DIALOGUE_PORTRAIT_SCALED_CACHE.clear()

