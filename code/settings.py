from pygame import Vector2
from utils import *
from hint_system import create_reward_state

# screen
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TILE_SIZE = 64

MUSIC = {
    'Serene': get_resource_path('audio/bg.ogg'),
    'Hope': get_resource_path('audio/Hope.ogg'),
    'Happy': get_resource_path('audio/Happy.ogg'),
    'Surf': get_resource_path('audio/Surf.ogg'),
}

MUSIC_NAME = MUSIC['Hope']

# Audio defaults shared by Player and Settings UI.
DEFAULT_MUSIC_VOLUME_PERCENT = 15
MUSIC_VOLUME_SCALE = 0.14


# Relative URL: the frontend hits /api/... on whatever origin it is served from,
# which an nginx reverse proxy forwards to the backend container. For local dev
# without a proxy, override to an absolute URL like 'http://localhost:8002'.
BACKEND_URL = '/api'


# overlay positions 
OVERLAY_POSITIONS = {
	'tool' : (40, SCREEN_HEIGHT - 15), 
	'seed': (70, SCREEN_HEIGHT - 5)}

PLAYER_TOOL_OFFSET = {
	'left': Vector2(-50,40),
	'right': Vector2(50,40),
	'up': Vector2(0,-10),
	'down': Vector2(0,50)
}

LAYERS = {
	'water': 0,
	'ground': 1,
	'soil': 2,
	'soil water': 3,
	'rain floor': 4,
	'house bottom': 5,
	'ground plant': 6,
	'main': 7,
	'house top': 8,
	'fruit': 9,
	'rain drops': 10
}

APPLE_POS = {
	'Small': [(18,17), (30,37), (12,50), (30,45), (20,30), (30,10)],
	'Large': [(30,24), (60,65), (50,50), (16,40),(45,50), (42,70)]
}


DEFAULT_INVENTORY = [{
                'wood': 3,
                'apple': 2,
                'corn': 0,
                'tomato': 0},
                {
                'corn': 5,
                'tomato': 5},
                200]


# Current scene/level identifier used by the save/load system.
# LabHero currently has one main map, but this field keeps the save format ready
# for future levels/scenes.
DEFAULT_SCENE_ID = 'main_map'

DEFAULT_PLAYER_STATE = {
    'scene': DEFAULT_SCENE_ID,
    'x': None,
    'y': None,
    'facing': 'down',
    'status': 'down_idle',
    'skin_id': 'default',
    'name_confirmed': False,
    # Historic saves default safely to Normal. Fresh New Games may replace
    # this value during Dr. Alves registration before any mission starts.
    'campaign_mode': 'normal',
    # STUDENT.2: the campaign-completion summary is shown once automatically.
    'final_results_seen': False,
    # One-time map easter egg. Historic saves safely default to not collected.
    'golden_egg_collected': False
}

DEFAULT_INVENTORY_2 = [
    "Margaret Dayhoff",
    [], #'List of Results'
    [], #'List of activated missions'
    [], #'List of completed missions'
    DEFAULT_PLAYER_STATE, #'Player position/orientation/scene'
    create_reward_state() #'Keys / hints / mission scores'
    ]
