"""Lazy direct launcher for TEACHER.1 mission previews."""

import importlib

from campaign import normalize_mission_id


def mission_info_class_name(mission_id):
    mission_id = normalize_mission_id(mission_id)
    return "Mission_info" if mission_id == "01" else f"Mission{mission_id}_info"


class TeacherMissionLauncher:
    def __init__(self, player, mission_id):
        self.player = player
        self.mission_id = normalize_mission_id(mission_id)

    def _build_menu(self):
        module = importlib.import_module(f"mission{self.mission_id}")
        menu_class = getattr(module, mission_info_class_name(self.mission_id))
        # The mission's own pygame-menu handles BACK/ESC. The callback exists
        # only for compatibility with the existing mission menu constructors.
        return menu_class(lambda: None, self.player)

    async def update(self):
        menu = self._build_menu()
        await menu.update()
