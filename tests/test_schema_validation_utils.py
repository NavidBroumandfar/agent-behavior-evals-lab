import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from schema_validation_utils import load_json_object, validate_schema_value


class UtilityValidationError(Exception):
    """Test-local validation error."""


class SchemaValidationUtilsTests(unittest.TestCase):
    def test_validates_nested_object_with_additional_property_schema(self):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["thresholds"],
            "properties": {
                "thresholds": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                    },
                }
            },
        }
        value = {"thresholds": {"generic_assistant": 10.0}}

        validate_schema_value(value, schema, "manifest", Path("manifest.json"), REPO_ROOT, UtilityValidationError)

    def test_rejects_unexpected_property_with_custom_error_type(self):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        }

        with self.assertRaisesRegex(UtilityValidationError, "unexpected fields: extra"):
            validate_schema_value({"extra": True}, schema, "manifest", Path("manifest.json"), REPO_ROOT, UtilityValidationError)

    def test_empty_root_context_does_not_prefix_object_errors(self):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["case_id"],
            "properties": {"case_id": {"type": "string"}},
        }

        with self.assertRaisesRegex(UtilityValidationError, "^missing required fields: case_id$"):
            validate_schema_value({}, schema, "", Path("cases.jsonl"), REPO_ROOT, UtilityValidationError)

    def test_load_json_object_uses_custom_error_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "value.json"
            json_path.write_text(json.dumps(["not", "object"]), encoding="utf-8")

            with self.assertRaisesRegex(UtilityValidationError, "must be a JSON object"):
                load_json_object(json_path, "manifest", REPO_ROOT, UtilityValidationError)


if __name__ == "__main__":
    unittest.main()
