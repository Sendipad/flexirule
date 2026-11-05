import test from "node:test";
import assert from "node:assert/strict";

import {
	generateCollectionAlias,
	RESERVED_ALIASES,
	toCanonicalFlexValue,
	safeCoerceInteger,
	safeCoerceDecimal,
	safeCoerceBoolean,
	deserializeConditionTree,
	serializeConditionTree,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_adapter.mjs";

import { normalizeConditionContract } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_contract_normalization.mjs";
import { validateCanonicalCondition } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_validation.mjs";

test("adapter: generateCollectionAlias avoids reserved aliases and generates safe deterministic names", () => {
	const alias1 = generateCollectionAlias("row");
	assert.notEqual(alias1, "row");
	assert.ok(!RESERVED_ALIASES.has(alias1));
	assert.match(alias1, /^[A-Za-z][A-Za-z0-9_]*$/);

	const alias2 = generateCollectionAlias("items");
	assert.equal(alias2, "items_row");
	assert.ok(!RESERVED_ALIASES.has(alias2));

	const alias3 = generateCollectionAlias("doc.child_items");
	assert.equal(alias3, "child_items_row");

	const existing = new Set(["items_row"]);
	const aliasCollision = generateCollectionAlias("items", existing);
	assert.equal(aliasCollision, "items_row_2");
});

test("adapter: toCanonicalFlexValue preserves 2-item arrays without corruption", () => {
	const listVal = toCanonicalFlexValue(["Open", "Closed"]);
	assert.deepEqual(listVal, {
		mode: "static",
		value_type: "list",
		value: ["Open", "Closed"],
	});

	const tupleVal = toCanonicalFlexValue(["Customer", "Cust-001"], "Link");
	assert.deepEqual(tupleVal, {
		mode: "static",
		value_type: "string",
		value: "Cust-001",
	});
});

test("adapter: strict coercion helpers reject invalid data without silent zeroing", () => {
	assert.equal(safeCoerceInteger(123), 123);
	assert.equal(safeCoerceInteger("456"), 456);
	assert.throws(() => safeCoerceInteger("abc"), TypeError);
	assert.throws(() => safeCoerceInteger("12.34"), TypeError);

	assert.equal(safeCoerceDecimal("12.34"), "12.34");
	assert.equal(safeCoerceDecimal(50), "50");
	assert.throws(() => safeCoerceDecimal("invalid"), TypeError);

	assert.equal(safeCoerceBoolean(true), true);
	assert.equal(safeCoerceBoolean(false), false);
	assert.equal(safeCoerceBoolean("true"), true);
	assert.equal(safeCoerceBoolean("false"), false);
	assert.throws(() => safeCoerceBoolean("invalid_bool"), TypeError);
});

test("contract: normalizeConditionContract maps operator DTO array to ID lookup map", () => {
	const rawBackendContract = {
		api_version: "1",
		limits: { condition_depth: 8, condition_nodes: 64, path_segments: 6 },
		operators: [
			{ id: "eq", label: "Equals", arity: 2, accepted_left_types: ["string", "decimal"], accepted_right_types: ["string", "decimal"] },
			{ id: "is_set", label: "Is set", arity: 1, accepted_left_types: ["string"] },
		],
	};

	const normalized = normalizeConditionContract(rawBackendContract);
	assert.ok(normalized.operators.eq);
	assert.equal(normalized.operators.eq.label, "Equals");
	assert.equal(normalized.operators.eq.arity, 2);
	assert.ok(normalized.operators.is_set);
	assert.equal(normalized.operators.is_set.arity, 1);
	assert.equal(normalized.operatorList.length, 2);
	assert.equal(normalized.limits.condition_depth, 8);
	assert.equal(normalized.limits.depth, 8);
});

test("adapter: double-encoded JSON and unknown roots are handled losslessly", () => {
	const singleEncoded = JSON.stringify({
		type: "comparison",
		operator: "eq",
		left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
		right: { mode: "static", value_type: "string", value: "Open" },
	});
	const doubleEncoded = JSON.stringify(singleEncoded);

	const tree = deserializeConditionTree(doubleEncoded);
	assert.equal(tree.children.length, 1);
	assert.equal(tree.children[0].operator, "eq");

	const unknownRoot = {
		type: "unknown_custom_condition_v99",
		custom_field: "special_value",
	};
	const preservedTree = deserializeConditionTree(unknownRoot);
	assert.equal(preservedTree.children.length, 1);
	assert.equal(preservedTree.children[0].is_unsupported, true);
	assert.deepEqual(preservedTree.children[0].original_payload, unknownRoot);

	const reserialized = serializeConditionTree(preservedTree);
	assert.deepEqual(reserialized, unknownRoot);
});

test("validation: unsupported condition fails validation to block save", () => {
	const treeWithUnsupported = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "leaf-1",
				type: "leaf",
				operator: "eq",
				is_unsupported: true,
				unsupported_reason: "Legacy condition pattern cannot be safely edited",
				original_payload: { raw: "doc.status == 'Open'" },
			},
		],
	};

	const result = validateCanonicalCondition(treeWithUnsupported, { isMandatory: false });
	assert.equal(result.valid, false);
	assert.ok(result.errors.some((e) => e.includes("Legacy condition pattern")));
});
