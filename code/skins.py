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
    """Discovers available skins eagerly and loads animation frames on demand."""

    def __init__(self, registry=None):
        self.registry = list(registry or SKIN_REGISTRY)
        self.skins = []
        self.animations_by_skin = {}
        self._skins_by_id = {}
        self._discover_skins()

    @staticmethod
    def _state_has_files(state_path):
        """Cheap structural check used without decoding any image surfaces."""
        for _, _, filenames in os.walk(state_path):
            if filenames:
                return True
        return False

    def _discover_skins(self):
        """Register structurally complete skins without loading their images."""
        for skin in self.registry:
            skin_root = get_resource_path(skin.folder)
            if not os.path.isdir(skin_root):
                # This allows keeping future skin entries here before the art exists.
                continue

            if not all(
                self._state_has_files(os.path.join(skin_root, state))
                for state in ANIMATION_STATES
            ):
                continue

            self.skins.append(skin)
            self._skins_by_id[skin.id] = skin

        if not self.skins:
            raise RuntimeError('No valid character skins were found.')

    def _discard_skin(self, skin_id):
        """Remove a skin if its files disappear between discovery and first use."""
        self.animations_by_skin.pop(skin_id, None)
        self._skins_by_id.pop(skin_id, None)
        self.skins = [skin for skin in self.skins if skin.id != skin_id]

    def _load_skin(self, skin_id):
        """Load one skin exactly once and return its cached animation mapping."""
        cached = self.animations_by_skin.get(skin_id)
        if cached is not None:
            return cached

        skin = self._skins_by_id.get(skin_id)
        if skin is None:
            return None

        skin_root = get_resource_path(skin.folder)
        animations = {}
        for state in ANIMATION_STATES:
            state_path = os.path.join(skin_root, state)
            frames = import_folder(state_path)
            if not frames:
                # The eager implementation excluded incomplete skins. Preserve
                # that behaviour if files vanish after the lightweight scan.
                self._discard_skin(skin_id)
                return None
            animations[state] = frames

        self.animations_by_skin[skin_id] = animations
        return animations

    def load_all_skins(self):
        """Compatibility helper for callers that explicitly want eager loading."""
        for skin_id in list(self.skin_ids()):
            self._load_skin(skin_id)

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
        return self._skins_by_id.get(skin_id, self.skins[0])

    def is_valid_skin(self, skin_id):
        # Validity describes an available registry entry, not whether its
        # animation surfaces happen to have been loaded already.
        return skin_id in self._skins_by_id

    def is_unlocked(self, skin_id, missions_completed=None):
        skin = self.get_skin(skin_id)
        if skin.unlocked:
            return True
        return mission_requirement_met(skin.unlock_after_mission, missions_completed)

    def get_animations(self, skin_id):
        target_id = skin_id if self.is_valid_skin(skin_id) else self.default_skin_id
        animations = self._load_skin(target_id)
        if animations is not None:
            return animations

        # A skin may have disappeared between discovery and first use. Fall
        # back exactly as the old manager did for an unavailable skin.
        if not self.skins:
            raise RuntimeError('No valid character skins were found.')

        fallback_id = self.default_skin_id
        animations = self._load_skin(fallback_id)
        if animations is None:
            raise RuntimeError('No valid character skins were found.')
        return animations

    def get_preview_surface(self, skin_id, state='down_idle'):
        animations = self.get_animations(skin_id)
        frames = animations.get(state) or animations.get('down_idle') or animations.get('down')
        return frames[0] if frames else None

    @property
    def default_skin_id(self):
        return self.skins[0].id
