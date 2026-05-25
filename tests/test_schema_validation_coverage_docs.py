import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "schemas"
COVERAGE_DOC_PATH = REPO_ROOT / "docs/wiki/reference/schema_validation_coverage.md"


class SchemaValidationCoverageDocsTests(unittest.TestCase):
    def test_coverage_doc_lists_every_schema_file(self):
        coverage_doc = COVERAGE_DOC_PATH.read_text(encoding="utf-8")
        documented_schemas = set(re.findall(r"schemas/[a-z_]+\.schema\.json", coverage_doc))
        actual_schemas = {str(path.relative_to(REPO_ROOT)) for path in SCHEMA_DIR.glob("*.schema.json")}

        self.assertEqual(documented_schemas, actual_schemas)

    def test_coverage_doc_marks_every_schema_as_shared_helper_validation(self):
        coverage_doc = COVERAGE_DOC_PATH.read_text(encoding="utf-8")
        schema_rows = [line for line in coverage_doc.splitlines() if line.startswith("| `schemas/")]
        actual_schemas = {str(path.relative_to(REPO_ROOT)) for path in SCHEMA_DIR.glob("*.schema.json")}

        self.assertEqual(len(schema_rows), len(actual_schemas))
        for row in schema_rows:
            self.assertIn("`src/schema_validation_utils.py`", row)
            self.assertNotIn("Contract implemented in local validator code", row)

    def test_coverage_doc_keeps_local_execution_boundary(self):
        coverage_doc = COVERAGE_DOC_PATH.read_text(encoding="utf-8")

        for required_phrase in [
            "do not call provider APIs",
            "run local files only",
            "Every file matching `schemas/*.schema.json` must appear",
            "Every schema row must identify `src/schema_validation_utils.py`",
        ]:
            self.assertIn(required_phrase, coverage_doc)


if __name__ == "__main__":
    unittest.main()
