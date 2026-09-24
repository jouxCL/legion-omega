import unittest
import json
from pathlib import Path
import sys

ROOT_V04 = Path(__file__).resolve().parent.parent / "Legion_Omega_V0.4_CREWAI"
if str(ROOT_V04) not in sys.path:
    sys.path.insert(0, str(ROOT_V04))

from flutter_builder.compiler import FlutterCompiler


class TestFlutterCompiler(unittest.TestCase):

    def test_parse_errors(self):
        compiler = FlutterCompiler("/tmp")
        raw_output = (
            "  error • The argument type 'String' can't be assigned • lib/main.dart:10:15 • argument_type_not_assignable\n"
            "lib/features/notes/presentation/note_page.dart:25:8: error: Undefined name 'NoteCubit'.\n"
            "lib/features/notes/presentation/note_page.dart:30:12: warning: Unused import.\n"
        )
        errs = compiler._parse_errors(raw_output)
        self.assertEqual(len(errs), 2)
        self.assertEqual(errs[0]["file"], "lib/features/notes/presentation/note_page.dart")
        self.assertEqual(errs[0]["line"], 25)
        self.assertEqual(errs[0]["col"], 8)
        self.assertEqual(errs[0]["error_type"], "compile_error")
        self.assertEqual(errs[1]["error_type"], "analyze_warning")


if __name__ == "__main__":
    unittest.main()
