import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from frc_snippet_check.cli import extract_blocks, load_rules, main, scan

FIXTURES = Path(__file__).parent / "fixtures"
RULES = load_rules()


def findings(name, target=2026, only_tagged=False):
    _, _, found = scan([str(FIXTURES / name)], RULES, only_tagged, target)
    return [(f.rule, f.severity, f.line) for f in found]


class RuleTests(unittest.TestCase):
    def test_current_code_is_clean(self):
        self.assertEqual(findings("01_current_ok.md"), [])

    def test_old_command_framework(self):
        self.assertEqual(findings("02_old_command.md"), [("old-command-framework", "error", 2)])

    def test_old_bindings_depend_on_target_year(self):
        self.assertEqual(findings("03_old_bindings.md"),
                         [("old-trigger-bindings", "error", 2), ("old-trigger-bindings", "error", 3)])
        self.assertEqual({s for _, s, _ in findings("03_old_bindings.md", 2023)}, {"warning"})
        self.assertEqual(findings("03_old_bindings.md", 2022), [])

    def test_language_tag_is_case_insensitive(self):
        self.assertEqual(findings("04_speed_controller_group.md"),
                         [("speed-controller-group", "error", 2)])

    def test_deprecated_then_removed(self):
        self.assertEqual({s for _, s, _ in findings("05_motor_controller_group.md")}, {"warning"})
        self.assertEqual({s for _, s, _ in findings("05_motor_controller_group.md", 2027)}, {"error"})
        self.assertEqual(findings("05_motor_controller_group.md", 2023), [])

    def test_moved_packages(self):
        self.assertEqual([r for r, _, _ in findings("06_moved_packages.md")],
                         ["math-packages-moved", "pwm-motor-controllers-moved"])

    def test_comments_and_prose_are_ignored(self):
        self.assertEqual(findings("07_comments_and_prose.md"), [])

    def test_non_java_blocks_are_ignored(self):
        self.assertEqual(findings("08_non_java.md"), [])

    def test_ignore_comment_and_skip_tag(self):
        self.assertEqual(findings("09_ignore_and_skip.md"), [])

    def test_multiple_rules_on_one_line(self):
        self.assertEqual(sorted(r for r, _, _ in findings("10_multi_rule.md")),
                         ["robot-drive", "speed-controller-group"])

    def test_indented_mkdocs_tabs(self):
        self.assertEqual(findings("11_mkdocs_tabs.md"), [("old-trigger-bindings", "error", 4)])

    def test_only_tagged(self):
        self.assertEqual(len(findings("12_tagged.md")), 2)
        self.assertEqual(findings("12_tagged.md", only_tagged=True), [("old-trigger-bindings", "error", 2)])


class ParserAndCliTests(unittest.TestCase):
    def test_tilde_fences_and_unclosed_block(self):
        blocks = extract_blocks("~~~java\na\n~~~\n```java\nb\n", "x.md")
        self.assertEqual([(b.lang, b.lines) for b in blocks], [("java", ["a"]), ("java", ["b"])])

    def test_every_rule_has_a_source_and_a_year(self):
        data = json.loads((Path(__file__).parents[1] / "frc_snippet_check/rules.json").read_text())
        for r in data["rules"]:
            self.assertTrue(r["source"], r["id"])
            self.assertTrue(r["deprecated_in"] or r["removed_in"], r["id"])
            if r["source"] == "unverified":
                self.assertIsNone(r["removed_in"], f"{r['id']}: unverified rules may only warn")

    def test_exit_codes(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(FIXTURES / "02_old_command.md")]), 1)
            self.assertEqual(main([str(FIXTURES / "05_motor_controller_group.md")]), 0)
            self.assertEqual(main(["--fail-on", "warning", str(FIXTURES / "05_motor_controller_group.md")]), 1)
            self.assertEqual(main(["--fail-on", "never", str(FIXTURES / "02_old_command.md")]), 0)

    def test_github_format(self):
        out = io.StringIO()
        with redirect_stdout(out):
            main(["--format", "github", "--fail-on", "never", str(FIXTURES / "02_old_command.md")])
        self.assertIn("::error file=", out.getvalue())
        self.assertIn(",line=2,", out.getvalue())


if __name__ == "__main__":
    unittest.main()
