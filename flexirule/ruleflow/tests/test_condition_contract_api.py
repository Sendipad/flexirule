import unittest
from unittest.mock import patch

import frappe

from flexirule.ruleflow.api import get_condition_contract


class TestConditionContractAPI(unittest.TestCase):
    @patch("flexirule.ruleflow.api.require_builder_access")
    def test_get_condition_contract_structure(self, mock_require_access):
        mock_require_access.return_value = True

        dto = get_condition_contract()

        mock_require_access.assert_called_once()
        self.assertEqual(dto["contract_version"], "1.0.0")
        self.assertIn("operators", dto)
        self.assertIn("resource_limits", dto)
        self.assertIn("permitted_scopes", dto)

        # Check resource limits
        limits = dto["resource_limits"]
        self.assertEqual(limits["max_condition_depth"], 32)
        self.assertEqual(limits["max_condition_nodes"], 1000)

        # Ensure eq operator exists
        op_ids = [op["id"] for op in dto["operators"]]
        self.assertIn("eq", op_ids)
        self.assertIn("is_submittable", op_ids)
        self.assertIn("has_field", op_ids)


if __name__ == "__main__":
    unittest.main()
