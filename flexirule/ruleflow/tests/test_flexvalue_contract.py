import unittest

from flexirule.ruleflow.core.flexvalue_contract import (
    FlexValueResolverRegistry,
    FlexValueValidationError,
    validate_flex_value,
)


class TestFlexValueContract(unittest.TestCase):
    def test_valid_static_flex_value(self):
        val = {"mode": "static", "value_type": "string", "value": "hello"}
        validate_flex_value(val)

        val_dec = {"mode": "static", "value_type": "decimal", "value": "123.45"}
        validate_flex_value(val_dec)

        val_bool = {"mode": "static", "value_type": "boolean", "value": True}
        validate_flex_value(val_bool)

        val_null = {"mode": "static", "value_type": "null", "value": None}
        validate_flex_value(val_null)

    def test_invalid_static_flex_value(self):
        with self.assertRaises(FlexValueValidationError):
            validate_flex_value({"mode": "static", "value_type": "boolean", "value": 1})

        with self.assertRaises(FlexValueValidationError):
            validate_flex_value({"mode": "static", "value_type": "decimal", "value": "abc"})

        with self.assertRaises(FlexValueValidationError):
            validate_flex_value({"mode": "static", "value_type": "string", "value": 123, "extra": 1})

    def test_valid_variable_flex_value(self):
        val = {
            "mode": "variable",
            "path": {"scope": "doc", "segments": ["status"]},
        }
        validate_flex_value(val)

    def test_invalid_variable_flex_value(self):
        with self.assertRaises(FlexValueValidationError):
            validate_flex_value(
                {"mode": "variable", "path": {"scope": "invalid_scope", "segments": ["a"]}}
            )

        with self.assertRaises(FlexValueValidationError):
            validate_flex_value(
                {"mode": "variable", "path": {"scope": "doc", "segments": ["__dunder__"]}}
            )

        with self.assertRaises(FlexValueValidationError):
            validate_flex_value({"mode": "variable", "path": {"scope": "doc", "segments": []}})

    def test_resolver_capability_default_deny(self):
        self.assertFalse(
            FlexValueResolverRegistry.is_allowed_as_condition_operand("math", "add")
        )

    def test_valid_template_flex_value(self):
        val = {
            "mode": "template",
            "segments": [
                "Hello ",
                {"mode": "variable", "path": {"scope": "doc", "segments": ["owner"]}},
            ],
        }
        validate_flex_value(val)


if __name__ == "__main__":
    unittest.main()
