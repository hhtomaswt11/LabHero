import sys
import os

APP_NAME = 'LabHero'

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

