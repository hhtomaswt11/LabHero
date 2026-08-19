import pygame

from hint_system import KEY_TYPES
from settings import SCREEN_WIDTH, SCREEN_HEIGHT
from utils import get_resource_path


class SkinSelectionMenu:
    """Unified inventory overlay with keys, score and skin selection."""

    KEY_LABELS = {
        'bronze': 'Bronze',
        'silver': 'Silver',
        'gold': 'Gold',
    }

    def __init__(self, skin_manager, player):
        self.skin_manager = skin_manager
        self.player = player
        self.display_surface = pygame.display.get_surface()
        self.font_title = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 48)
        self.font = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 30)
        self.font_small = pygame.font.Font(get_resource_path('font/LycheeSoda.ttf'), 22)

        self.opened = False
        self.original_skin_id = skin_manager.default_skin_id
        self.selected_index = 0
        self.key_locks = {
            pygame.K_LEFT: False,
            pygame.K_RIGHT: False,
            pygame.K_a: False,
            pygame.K_d: False,
            pygame.K_e: False,
            pygame.K_RETURN: False,
            pygame.K_KP_ENTER: False,
            pygame.K_ESCAPE: False,
        }
        self.feedback_text = ''
        self.key_icons = self._load_key_icons()

    def _load_key_icons(self):
        """Load a visible key set once for the inventory overlay."""
        icon_paths = {
            'bronze': 'graphics/keys/Key 3/key3_bronze.png',
            'silver': 'graphics/keys/Key 3/key3_silver.png',
            'gold': 'graphics/keys/Key 3/key3_gold.png',
            'grey': 'graphics/keys/Key 3/key3_grey.png',
        }
        icons = {}
        for key_type, relative_path in icon_paths.items():
            icon = pygame.image.load(get_resource_path(relative_path)).convert_alpha()
            icons[key_type] = pygame.transform.scale(icon, (24, 40))
        return icons

    def open(self):
        self.opened = True
        self.original_skin_id = self.player.current_skin_id
        ids = [skin.id for skin in self._visible_skins()]
        self.selected_index = ids.index(self.original_skin_id) if self.original_skin_id in ids else 0
        self.feedback_text = ''

        # Prevent the key used to open the overlay from immediately acting again.
        keys = pygame.key.get_pressed()
        for key in self.key_locks:
            self.key_locks[key] = keys[key]

    def _pressed_once(self, key):
        keys = pygame.key.get_pressed()
        pressed = keys[key]
        once = pressed and not self.key_locks.get(key, False)
        self.key_locks[key] = pressed
        return once

    def _visible_skins(self):
        return self.skin_manager.unlocked_skins(self.player.missions_completed)

    def _selected_skin(self):
        skins = self._visible_skins()
        if not skins:
            return self.skin_manager.get_skin(self.skin_manager.default_skin_id)
        self.selected_index %= len(skins)
        return skins[self.selected_index]

    def _move_selection(self, step):
        count = len(self._visible_skins())
        if count:
            self.selected_index = (self.selected_index + step) % count
            self.feedback_text = ''

    def _score_summary(self):
        total = self.player.hint_system.get_total_score()
        maximum = self.player.hint_system.get_max_score(40)
        return f'{total} / {maximum}'

    def update(self):
        """Returns: 'confirm', 'cancel' or None."""
        # Read all relevant keys first (avoids short-circuit skipping a lock update).
        left_pressed = self._pressed_once(pygame.K_LEFT)
        a_pressed = self._pressed_once(pygame.K_a)
        right_pressed = self._pressed_once(pygame.K_RIGHT)
        d_pressed = self._pressed_once(pygame.K_d)

        if left_pressed or a_pressed:
            self._move_selection(-1)

        if right_pressed or d_pressed:
            self._move_selection(1)

        close_pressed = (
            self._pressed_once(pygame.K_ESCAPE)
            or self._pressed_once(pygame.K_e)
        )
        if close_pressed:
            self.player.set_skin(self.original_skin_id)
            self.opened = False
            return 'cancel'

        confirm_pressed = (
            self._pressed_once(pygame.K_RETURN)
            or self._pressed_once(pygame.K_KP_ENTER)
        )
        if confirm_pressed:
            skin = self._selected_skin()
            if self.skin_manager.is_unlocked(skin.id, self.player.missions_completed):
                self.player.set_skin(skin.id)
                self.opened = False
                return 'confirm'
            self.feedback_text = 'Locked skin.'

        return None

    def _draw_key_row(self, panel, key_type, index):
        count = self.player.hint_system.get_key_count(key_type)
        icon_key = key_type if count > 0 else 'grey'
        icon = self.key_icons[icon_key]
        y = panel.y + 108 + index * 52
        self.display_surface.blit(icon, (panel.x + 34, y - 6))

        label = self.font.render(self.KEY_LABELS[key_type], False, 'black')
        self.display_surface.blit(label, (panel.x + 72, y))

        value = self.font.render(str(count), False, 'black')
        self.display_surface.blit(value, (panel.x + 220, y))

    def draw(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.display_surface.blit(overlay, (0, 0))

        panel = pygame.Rect(36, 28, 640, 318)
        pygame.draw.rect(self.display_surface, (240, 240, 240), panel, border_radius=8)
        pygame.draw.rect(self.display_surface, (40, 40, 40), panel, 4, border_radius=8)

        title = self.font_title.render('Inventory', False, 'black')
        self.display_surface.blit(title, (panel.x + 20, panel.y + 16))

        # Left column: keys + score.
        keys_title = self.font.render('KEYS', False, 'black')
        self.display_surface.blit(keys_title, (panel.x + 28, panel.y + 72))
        for index, key_type in enumerate(KEY_TYPES):
            self._draw_key_row(panel, key_type, index)

        score_title = self.font.render('SCORE', False, 'black')
        self.display_surface.blit(score_title, (panel.x + 28, panel.y + 246))
        score_value = self.font.render(self._score_summary(), False, 'black')
        self.display_surface.blit(score_value, (panel.x + 150, panel.y + 246))

        # Right column: skin preview and selection.
        divider_x = panel.x + 314
        pygame.draw.line(
            self.display_surface,
            (140, 140, 140),
            (divider_x, panel.y + 74),
            (divider_x, panel.bottom - 56),
            2,
        )

        skin_title = self.font.render('SKIN', False, 'black')
        self.display_surface.blit(skin_title, (divider_x + 30, panel.y + 72))

        skin = self._selected_skin()
        preview = self.skin_manager.get_preview_surface(skin.id)
        if preview:
            preview = pygame.transform.scale(preview, (110, 80))
            preview_rect = preview.get_rect(topleft=(divider_x + 38, panel.y + 122))
            pygame.draw.rect(self.display_surface, (255, 255, 255), preview_rect.inflate(20, 20), border_radius=5)
            pygame.draw.rect(self.display_surface, (120, 120, 120), preview_rect.inflate(20, 20), 2, border_radius=5)
            self.display_surface.blit(preview, preview_rect)

        name_surf = self.font.render(skin.name, False, 'black')
        name_rect = name_surf.get_rect(center=(divider_x + 156, panel.y + 238))
        self.display_surface.blit(name_surf, name_rect)

        status = 'Unlocked' if self.skin_manager.is_unlocked(skin.id, self.player.missions_completed) else 'Locked'
        status_surf = self.font_small.render(f'Status: {status}', False, 'black')
        status_rect = status_surf.get_rect(center=(divider_x + 156, panel.y + 268))
        self.display_surface.blit(status_surf, status_rect)

        controls = 'E / Esc close    < / > change skin    Enter apply skin'
        controls_surf = self.font_small.render(controls, False, 'black')
        self.display_surface.blit(controls_surf, (panel.x + 18, panel.bottom - 44))

        if self.feedback_text:
            feedback = self.font_small.render(self.feedback_text, False, 'red')
            self.display_surface.blit(feedback, (panel.x + 18, panel.bottom - 20))
