import pygame

from settings import SCREEN_WIDTH, SCREEN_HEIGHT
from utils import get_resource_path


class SkinSelectionMenu:
    """Small pause overlay used to preview and confirm player skins."""

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
            pygame.K_c: False,
            pygame.K_RETURN: False,
            pygame.K_KP_ENTER: False,
            pygame.K_ESCAPE: False,
        }
        self.feedback_text = ''

    def open(self):
        self.opened = True
        self.original_skin_id = self.player.current_skin_id
        ids = self.skin_manager.skin_ids()
        self.selected_index = ids.index(self.original_skin_id) if self.original_skin_id in ids else 0
        self.feedback_text = ''

        # Prevent the C key used to open the overlay from immediately confirming.
        keys = pygame.key.get_pressed()
        for key in self.key_locks:
            self.key_locks[key] = keys[key]

    def _pressed_once(self, key):
        keys = pygame.key.get_pressed()
        pressed = keys[key]
        once = pressed and not self.key_locks.get(key, False)
        self.key_locks[key] = pressed
        return once

    def _selected_skin(self):
        return self.skin_manager.skins[self.selected_index]

    def _move_selection(self, step):
        count = len(self.skin_manager.skins)
        if count:
            self.selected_index = (self.selected_index + step) % count
            self.feedback_text = ''

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

        if self._pressed_once(pygame.K_ESCAPE):
            self.player.set_skin(self.original_skin_id)
            self.opened = False
            return 'cancel'

        # Confirming is Enter-only now. K_c is intentionally NOT read here:
        # it's reserved for opening/closing the overlay elsewhere in the code.
        # Its lock is kept in sync via open() so it doesn't trigger a false
        # confirm on the frame the menu is opened.
        confirm_pressed = (
            self._pressed_once(pygame.K_RETURN)
            or self._pressed_once(pygame.K_KP_ENTER)
        )
        if confirm_pressed:
            skin = self._selected_skin()
            if skin.unlocked:
                self.player.set_skin(skin.id)
                self.opened = False
                return 'confirm'
            self.feedback_text = 'Locked skin. Unlocking can be connected later.'

        return None

    def draw(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.display_surface.blit(overlay, (0, 0))

        panel = pygame.Rect(32, 32, 450, 260)
        pygame.draw.rect(self.display_surface, (240, 240, 240), panel, border_radius=8)
        pygame.draw.rect(self.display_surface, (40, 40, 40), panel, 4, border_radius=8)

        title = self.font_title.render('Choose Skin', False, 'black')
        self.display_surface.blit(title, (panel.x + 20, panel.y + 16))

        skin = self._selected_skin()
        preview = self.skin_manager.get_preview_surface(skin.id)
        if preview:
            preview = pygame.transform.scale(preview, (86, 62))
            preview_rect = preview.get_rect(topleft=(panel.x + 30, panel.y + 95))
            pygame.draw.rect(self.display_surface, (255, 255, 255), preview_rect.inflate(18, 18), border_radius=5)
            self.display_surface.blit(preview, preview_rect)

        status = 'Unlocked' if skin.unlocked else 'Locked'
        # price_text = 'Free' if skin.price == 0 else f'{skin.price} coins'
        lines = [
            f'{skin.name}',
            # f'Status: {status}',
            # f'Price: {price_text}',
        ]
        for idx, line in enumerate(lines):
            surf = self.font.render(line, False, 'black')
            self.display_surface.blit(surf, (panel.x + 145, panel.y + 92 + idx * 34))

        controls = '< / > change    Enter confirm    Esc cancel'
        controls_surf = self.font_small.render(controls, False, 'black')
        self.display_surface.blit(controls_surf, (panel.x + 20, panel.bottom - 46))

        if self.feedback_text:
            feedback = self.font_small.render(self.feedback_text, False, 'red')
            self.display_surface.blit(feedback, (panel.x + 20, panel.bottom - 22))