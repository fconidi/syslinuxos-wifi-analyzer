import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))

import ast
from string import Formatter

from i18n import SUPPORTED, TRANSLATIONS, detect_language, scan_message, tr


class LocaleTests(unittest.TestCase):
    def test_supported_regions_and_fallback(self):
        for locale, expected in [('it_IT.UTF-8', 'it'), ('fr_CA', 'fr'),
                                 ('de_DE@euro', 'de'), ('es-MX', 'es'),
                                 ('en_GB.UTF-8', 'en'), ('pt_BR', 'en'),
                                 ('C.UTF-8', 'en'), ('POSIX', 'en'), ('', 'en')]:
            with self.subTest(locale=locale):
                self.assertEqual(detect_language({'LANG': locale}), expected)

    def test_session_precedence_and_language_preferences(self):
        cases = [({'LANG': 'it_IT', 'LC_MESSAGES': 'fr_FR'}, 'fr'),
                 ({'LANG': 'it_IT', 'LC_MESSAGES': 'fr_FR', 'LC_ALL': 'de_DE'}, 'de'),
                 ({'LANG': 'it_IT', 'LANGUAGE': 'pt_BR:es_ES:en'}, 'es'),
                 ({'LANG': 'it_IT', 'LANGUAGE': 'en:fr'}, 'en'),
                 ({'LANG': 'C', 'LANGUAGE': 'it'}, 'en'),
                 ({'LANG': 'it_IT', 'LC_ALL': 'C.UTF-8', 'LANGUAGE': 'fr'}, 'en'),
                 ({'LANG': 'de_DE', 'LANGUAGE': 'pt:ja'}, 'en')]
        for env, expected in cases:
            with self.subTest(env=env):
                self.assertEqual(detect_language(env), expected)

    def test_translation_and_formatting_follow_session(self):
        for language, expected in [('en', '&Start scan'), ('it', '&Avvia scansione'),
                                   ('fr', '&Démarrer le scan'), ('de', 'Scan s&tarten'),
                                   ('es', '&Iniciar escaneo')]:
            with patch.dict(os.environ, {'LANG': language}, clear=True):
                self.assertEqual(tr('&Start scan'), expected)
                self.assertIn('5180', tr('Target channel scan · {frequency} MHz', frequency=5180))
                self.assertEqual(tr('Unknown diagnostic'), 'Unknown diagnostic')

    def test_catalogs_cover_source_strings_and_keep_placeholders(self):
        fields = lambda text: {field for _, field, _, _ in Formatter().parse(text) if field}
        for source, translations in TRANSLATIONS.items():
            self.assertEqual(len(translations), len(SUPPORTED) - 1)
            for translation in translations:
                self.assertTrue(translation.strip())
                self.assertEqual(fields(source), fields(translation), source)
        for path in Path(__file__).resolve().parents[1].joinpath('source').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == 'tr' and node.args
                        and isinstance(node.args[0], ast.Constant)):
                    self.assertIn(node.args[0].value, TRANSLATIONS, str(path))

    def test_keyboard_shortcuts_do_not_clash_in_any_language(self):
        windows = [['&WiFi adapter:', '&Start scan', 'Si&gnal…'],
                   ['&WiFi adapter:', 'S&top scan', 'Si&gnal…'],
                   ['&Sensitivity:', '&Enable beeps', '&Volume:', '&Close Signal']]
        for index, language in enumerate(SUPPORTED):
            for keys in windows:
                marks = []
                for key in keys:
                    text = key if index == 0 else TRANSLATIONS[key][index - 1]
                    marks.append(text[text.index('&') + 1].lower())
                self.assertEqual(len(marks), len(set(marks)), (language, keys, marks))

    def test_backend_error_is_translated_without_formatting_raw_diagnostics(self):
        with patch.dict(os.environ, {'LANG': 'fr_FR'}, clear=True):
            self.assertEqual(scan_message('Adapter busy: waiting before retrying.'),
                             'Adaptateur occupé : attente avant une nouvelle tentative.')
            self.assertEqual(scan_message('Scan failed: driver {error}'),
                             'Échec du scan : driver {error}')


if __name__ == '__main__':
    unittest.main()
