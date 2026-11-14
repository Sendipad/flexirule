import test from "node:test";
import assert from "node:assert/strict";
import { searchSourceCatalogue } from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/source_catalogue.mjs";
import { toCanonicalFlexValue } from "../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_adapter.mjs";
import { ControlRegistry } from "../../../../../flexirule/public/js/flexirule/core/control_registry.js";

test("lifecycle: field-first and resolver suggestion policy filters out unauthorized operands", () => {
	const mockContract = {
		flexvalue_modes: {
			resolver: [
				{
					family: "math",
					operation: "formula",
					condition_operand_allowed: true,
					permission_policy: "no_data_access",
				},
				{
					family: "lookup",
					operation: "fetch",
					condition_operand_allowed: false,
					permission_policy: "authorized_read",
				},
			],
		},
	};

	const catalogue = [
		{
			id: "math_formula",
			family: "math",
			operation: "formula",
			sourceType: "resolver",
			category: "resolvers",
			searchTerms: ["math", "formula"],
		},
		{
			id: "lookup",
			family: "lookup",
			operation: "fetch",
			sourceType: "resolver",
			category: "resolvers",
			searchTerms: ["lookup", "fetch"],
		},
		{ id: "doc.status", sourceType: "field", category: "fields", searchTerms: ["status"] },
	];

	// With conditionContract supplied in left operand context, lookup.fetch must be filtered out
	const leftResults = searchSourceCatalogue(catalogue, "", {
		isLeftOperand: true,
		conditionContract: mockContract,
	});

	assert.strictEqual(
		leftResults.some((r) => r.id === "lookup"),
		false
	);
	assert.strictEqual(
		leftResults.some((r) => r.id === "math_formula"),
		true
	);
	assert.strictEqual(leftResults[0].id, "doc.status"); // Field-first priority
});

test("lifecycle: right operand A -> B -> A hydration preserves exact static and dynamic types", () => {
	// A: static number
	const stateA = { mode: "static", value_type: "Int", value: 100 };
	const canonA = toCanonicalFlexValue(stateA, "Int", "eq");
	assert.strictEqual(canonA.mode, "static");
	assert.strictEqual(canonA.value, 100);

	// B: variable path
	const stateB = { mode: "variable", path: { scope: "doc", segments: ["total_amount"] } };
	const canonB = toCanonicalFlexValue(stateB, "Int", "eq");
	assert.strictEqual(canonB.mode, "variable");
	assert.strictEqual(canonB.path.scope, "doc");
	assert.deepStrictEqual(canonB.path.segments, ["total_amount"]);

	// Revert to A: static number restored identically
	const stateA2 = { mode: "static", value_type: "Int", value: 100 };
	const canonA2 = toCanonicalFlexValue(stateA2, "Int", "eq");
	assert.deepStrictEqual(canonA, canonA2);
});

test("lifecycle: Link field with target DocType preserves exact string identity without date misclassification", () => {
	const linkVal = { mode: "static", value_type: "Link", value: "2026-11-08" };
	const canon = toCanonicalFlexValue(linkVal, "Link", "eq");
	assert.strictEqual(canon.mode, "static");
	assert.strictEqual(canon.value, "2026-11-08");
	assert.strictEqual(canon.value_type, "string"); // Preserved as string, never converted to date
});

test("lifecycle: an explicitly empty backend resolver allow-list hides every condition resolver", () => {
	const catalogue = [
		{
			id: "math_formula",
			family: "math",
			operation: "formula",
			sourceType: "resolver",
			category: "resolvers",
			searchTerms: ["math", "formula"],
		},
		{
			id: "date_time",
			family: "date_time",
			operation: "calculate",
			sourceType: "resolver",
			category: "resolvers",
			searchTerms: ["date", "calculate"],
		},
		{ id: "doc.status", sourceType: "field", category: "fields", searchTerms: ["status"] },
	];

	const results = searchSourceCatalogue(catalogue, "", {
		isLeftOperand: true,
		conditionContract: { flexvalue_modes: { resolver: [] } },
	});

	assert.deepEqual(
		results.map((item) => item.id),
		["doc.status"]
	);
});

test("lifecycle: Check DocField resolves through the existing native CheckControl mapping", () => {
	const resolved = ControlRegistry.resolve(
		{ fieldtype: "Check", label: "Enabled" },
		{ doc: { doctype: "Sales Invoice" } }
	);
	assert.equal(resolved.component, "CheckControl");
});
