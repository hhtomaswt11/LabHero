"""Regression tests for reusable Tiled Books interactions and bookshelf SFX."""
from __future__ import annotations

import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / 'code' / 'player.py'
LEVEL = ROOT / 'code' / 'level.py'
TMX = ROOT / 'data' / 'map_lb.tmx'
BOOK_AUDIO = ROOT / 'audio' / 'book.ogg'


class BooksInteractionTests(unittest.TestCase):
    def test_all_tiled_books_boxes_are_valid_player_interactions(self):
        root = ET.parse(TMX).getroot()
        player_layer = next(
            group for group in root.findall('objectgroup')
            if group.attrib.get('name') == 'Player'
        )
        books = [
            obj for obj in player_layer.findall('object')
            if obj.attrib.get('name') == 'Books'
        ]

        # Four original interactions plus the six newly-authored shelves.
        self.assertEqual(len(books), 10)
        for obj in books:
            self.assertGreater(float(obj.attrib.get('width', 0)), 0)
            self.assertGreater(float(obj.attrib.get('height', 0)), 0)

    def test_level_registers_books_generically_not_by_object_id(self):
        source = LEVEL.read_text(encoding='utf-8')
        self.assertIn("if obj.name == 'Books':", source)
        self.assertIn(
            "Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)",
            source,
        )

    def test_book_sound_asset_is_loaded_as_ogg(self):
        source = PLAYER.read_text(encoding='utf-8')
        self.assertTrue(BOOK_AUDIO.is_file())
        self.assertEqual(BOOK_AUDIO.read_bytes()[:4], b'OggS')
        self.assertIn("get_resource_path('audio/book.ogg')", source)
        self.assertIn('self.book_sound = pygame.mixer.Sound(book_sound_path)', source)
        self.assertIn('self.book_sound.set_volume(0.65)', source)

    def test_books_interaction_plays_sound_then_opens_existing_menu(self):
        source = PLAYER.read_text(encoding='utf-8')
        block = """elif collided_interaction_sprite[0].name == 'Books':\n                        self.book_sound.play()\n                        self.books()"""
        self.assertIn(block, source)

    def test_changes_do_not_replace_the_existing_books_menu(self):
        level_source = LEVEL.read_text(encoding='utf-8')
        books_source = (ROOT / 'code' / 'books.py').read_text(encoding='utf-8')
        self.assertIn('self.books = Books(self.read_books)', level_source)
        self.assertIn("title='Books'", books_source)
        self.assertIn('for book in BOOK_LIBRARY:', books_source)

    def test_python_sources_parse(self):
        ast.parse(PLAYER.read_text(encoding='utf-8'))
        ast.parse(LEVEL.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
