import ast
import configparser
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'pygbag.ini'


def _dependency_lists():
    parser = configparser.ConfigParser()
    parser.read(CONFIG, encoding='utf-8')
    section = parser['DEPENDENCIES']
    return (
        list(ast.literal_eval(section.get('ignoreDirs', '[]'))),
        list(ast.literal_eval(section.get('ignoreFiles', '[]'))),
    )


class CheckpointD3AWebBundleTests(unittest.TestCase):
    def test_development_only_directories_are_not_bundled(self):
        ignore_dirs, _ = _dependency_lists()
        expected = {
            '/tests',
            '/backup_map',
            '/planning',
            '/deploy',
            '/data/books',
            '/data/missions',
        }
        self.assertTrue(expected.issubset(set(ignore_dirs)))
        self.assertTrue(all(path.startswith('/') for path in ignore_dirs))

    def test_obsolete_iml1515_files_are_not_bundled(self):
        _, ignore_files = _dependency_lists()
        self.assertIn('iML1515.xml', ignore_files)
        self.assertIn('iML1515.xml.gz', ignore_files)

        # These files are development-only: no runtime Python source should
        # depend on them before we remove them from the browser archive.
        runtime_sources = [ROOT / 'main.py', ROOT / 'LabHero.py']
        runtime_sources.extend(sorted((ROOT / 'code').glob('*.py')))
        references = []
        for source in runtime_sources:
            text = source.read_text(encoding='utf-8', errors='ignore')
            if 'iML1515' in text:
                references.append(source.relative_to(ROOT).as_posix())
        self.assertEqual(references, [])

    def test_documentation_directories_are_not_runtime_dependencies(self):
        runtime_sources = [ROOT / 'main.py', ROOT / 'LabHero.py']
        runtime_sources.extend(sorted((ROOT / 'code').glob('*.py')))
        forbidden = ('data/books/', 'data/missions/')
        references = []
        for source in runtime_sources:
            text = source.read_text(encoding='utf-8', errors='ignore')
            for path in forbidden:
                if path in text:
                    references.append((source.relative_to(ROOT).as_posix(), path))
        self.assertEqual(references, [])

    def test_required_browser_assets_remain_available(self):
        ignore_dirs, ignore_files = _dependency_lists()

        # Do not accidentally exclude runtime trees while trimming developer
        # artefacts.  In particular the browser UI still reads the E. coli
        # SBML file for gene labels and both models' JSON metadata.
        protected_dirs = {'/code', '/graphics', '/audio', '/font', '/data/models', '/data/Tilesets'}
        self.assertTrue(protected_dirs.isdisjoint(set(ignore_dirs)))

        protected_files = {
            'map_lb.tmx',
            'ground_lb.png',
            'e_coli_core.xml.gz',
            'e_coli_core_meta.json',
            'iMM904.xml.gz',
            'iMM904_meta.json',
        }
        self.assertTrue(protected_files.isdisjoint(set(ignore_files)))

        required_paths = (
            ROOT / 'data' / 'map_lb.tmx',
            ROOT / 'graphics' / 'world' / 'ground_lb.png',
            ROOT / 'data' / 'models' / 'e_coli_core.xml.gz',
            ROOT / 'data' / 'models' / 'e_coli_core_meta.json',
            ROOT / 'data' / 'models' / 'iMM904.xml.gz',
            ROOT / 'data' / 'models' / 'iMM904_meta.json',
        )
        for path in required_paths:
            self.assertTrue(path.is_file(), path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    unittest.main()
