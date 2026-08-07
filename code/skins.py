import os
from dataclasses import dataclass

from functions import import_folder
from utils import get_resource_path
from progression import mission_requirement_met, unlock_requirement


ANIMATION_STATES = (
    'up', 'down', 'left', 'right',
    'up_idle', 'down_idle', 'left_idle', 'right_idle'
)


@dataclass(frozen=True)
class SkinDefinition:
    id: str
    name: str
    folder: str
    # price: int = 0
    unlocked: bool = True
    unlock_after_mission: str | None = None


# To add a new skin later: add one entry here and create the folder with the
# same animation subfolders as graphics/character/.
SKIN_REGISTRY = [
    SkinDefinition(
        id='default',
        name='Classic LabHero',
        folder='graphics/character',
        # price=0,
        unlocked=True
    ),
    SkinDefinition(
        id='alt',
        name='Scarlet LabHero',
        folder='graphics/character_alt',
        # price=0,
        unlocked=True
    ),
    SkinDefinition(
        id='alt2',
        name='Toxic LabHero',
        folder='graphics/character_alt2',
        # price=0,
        unlocked=True
    ),
    SkinDefinition(
        id='alt3',
        name='Amber LabHero',
        folder='graphics/character_alt3',
        # price=0,
        unlocked=True
    ),
    SkinDefinition(
        id='alt4',
        name='Blaze LabHero',
        folder='graphics/character_alt4',
        # price=0,
        unlocked=True
    ),
    SkinDefinition(
        id='alt5',
        name='Lilac LabHero',
        folder='graphics/character_alt5',
        # price=0,
        unlocked=True
    ),
    SkinDefinition(
        id='golden',
        name='Golden LabHero',
        folder='graphics/character_golden',
        # price=0,
        unlocked=False,
        unlock_after_mission=unlock_requirement('skin', 'golden'),
    ),
]


class SkinManager:
    """Loads every available skin once and serves cached animation frames."""

    def __init__(self, registry=None):
        self.registry = list(registry or SKIN_REGISTRY)
        self.skins = []
        self.animations_by_skin = {}
        self.load_all_skins()

    def load_all_skins(self):
        for skin in self.registry:
            skin_root = get_resource_path(skin.folder)
            if not os.path.isdir(skin_root):
                # This allows keeping future skin entries here before the art exists.
                continue

            animations = {}
            valid = True
            for state in ANIMATION_STATES:
                state_path = os.path.join(skin_root, state)
                frames = import_folder(state_path)
                if not frames:
                    valid = False
                    break
                animations[state] = frames

            if valid:
                self.skins.append(skin)
                self.animations_by_skin[skin.id] = animations

        if not self.skins:
            raise RuntimeError('No valid character skins were found.')

    def skin_ids(self, missions_completed=None, include_locked=True):
        skins = self.skins if include_locked else self.unlocked_skins(missions_completed)
        return [skin.id for skin in skins]

    def unlocked_skins(self, missions_completed=None):
        return [
            skin for skin in self.skins
            if self.is_unlocked(skin.id, missions_completed)
        ]

    def get_skin(self, skin_id):
        for skin in self.skins:
            if skin.id == skin_id:
                return skin
        return self.skins[0]

    def is_valid_skin(self, skin_id):
        return skin_id in self.animations_by_skin

    def is_unlocked(self, skin_id, missions_completed=None):
        skin = self.get_skin(skin_id)
        if skin.unlocked:
            return True
        return mission_requirement_met(skin.unlock_after_mission, missions_completed)

    def get_animations(self, skin_id):
        if skin_id not in self.animations_by_skin:
            skin_id = self.skins[0].id
        return self.animations_by_skin[skin_id]

    def get_preview_surface(self, skin_id, state='down_idle'):
        animations = self.get_animations(skin_id)
        frames = animations.get(state) or animations.get('down_idle') or animations.get('down')
        return frames[0] if frames else None

    @property
    def default_skin_id(self):
        return self.skins[0].id
