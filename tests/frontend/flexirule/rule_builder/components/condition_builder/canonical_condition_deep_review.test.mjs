import test from "node:test";
import assert from "node:assert/strict";

import {
	generateCollectionAlias,
	getCollectionSiblingAliases,
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

	// Test full RESERVED_ALIASES repair on deserialization
	for (const reserved of ["row", "item", "doc", "old_doc", "vars", "loop"]) {
		const legacyWithReserved = {
			type: "collection_predicate",
			quantifier: "any",
			source: { scope: "doc", segments: ["items"] },
			as: reserved,
			where: {
				type: "comparison",
				operator: "eq",
				left: { mode: "variable", path: { scope: reserved, segments: ["item_code"] } },
				right: { mode: "static", value_type: "string", value: "ITEM-001" },
			},
		};

		const deserialized = deserializeConditionTree(legacyWithReserved);
		const colNode = deserialized.children[0];
		assert.notEqual(colNode.alias, reserved);
		assert.ok(!RESERVED_ALIASES.has(colNode.alias));
		// Subtree variable references are updated to the repaired alias
		assert.equal(colNode.children[0].left.path.scope, colNode.alias);

		// Re-serialization persists the repaired condition
		const reserialized = serializeConditionTree(deserialized);
		assert.equal(reserialized.as, colNode.alias);
		assert.equal(reserialized.where.left.path.scope, colNode.alias);
	}
});

test("adapter: toCanonicalFlexValue preserves 2-item arrays without corruption", () => {
	const listVal = toCanonicalFlexValue(["Open", "Closed"]);
	assert.deepEqual(listVal, {
		mode: "static",
		value_type: "list",
		value: ["Open", "Closed"],
	});

	const tupleVal = toCanonicalFlexValue(["Customer", "Cust-001"], "Link", "eq");
	assert.deepEqual(tupleVal, {
		mode: "static",
		value_type: "string",
		value: "Cust-001",
	});

	// Two-item Link membership list with 'in' operator MUST NOT be unwrapped
	const linkMembership2 = toCanonicalFlexValue(["Customer A", "Customer B"], "Link", "in");
	assert.deepEqual(linkMembership2, {
		mode: "static",
		value_type: "list",
		value: ["Customer A", "Customer B"],
	});

	// Two-item Link membership list with 'not_in' operator
	const linkMembership2NotIn = toCanonicalFlexValue(
		["Customer A", "Customer B"],
		"Link",
		"not_in"
	);
	assert.deepEqual(linkMembership2NotIn, {
		mode: "static",
		value_type: "list",
		value: ["Customer A", "Customer B"],
	});

	// Three-item Link membership list with 'in' operator
	const linkMembership3 = toCanonicalFlexValue(
		["Customer A", "Customer B", "Customer C"],
		"Link",
		"in"
	);
	assert.deepEqual(linkMembership3, {
		mode: "static",
		value_type: "list",
		value: ["Customer A", "Customer B", "Customer C"],
	});

	// Dynamic Link field with 'in' operator
	const dynamicLinkMembership = toCanonicalFlexValue(["Doc A", "Doc B"], "Dynamic Link", "in");
	assert.deepEqual(dynamicLinkMembership, {
		mode: "static",
		value_type: "list",
		value: ["Doc A", "Doc B"],
	});
});

test("adapter: strict coercion helpers reject invalid data without silent zeroing", () => {
	assert.equal(safeCoerceInteger(123), 123);
	assert.equal(safeCoerceInteger("456"), 456);
	assert.throws(() => safeCoerceInteger("abc"), TypeError);
	assert.throws(() => safeCoerceInteger("12.34"), TypeError);
	assert.throws(() => safeCoerceInteger(12.34), TypeError);

	assert.equal(safeCoerceDecimal("12.34"), "12.34");
	assert.equal(safeCoerceDecimal(50), "50");
	assert.throws(() => safeCoerceDecimal("invalid"), TypeError);

	assert.equal(safeCoerceBoolean(true), true);
	assert.equal(safeCoerceBoolean(false), false);
	assert.equal(safeCoerceBoolean("true"), true);
	assert.equal(safeCoerceBoolean("false"), false);
	assert.throws(() => safeCoerceBoolean("invalid_bool"), TypeError);

	// Production toCanonicalFlexValue path refuses invalid values and throws instead of falling back
	assert.throws(() => toCanonicalFlexValue("12.34", "Int"), TypeError);
	assert.throws(() => toCanonicalFlexValue(12.34, "Int"), TypeError);
	assert.throws(() => toCanonicalFlexValue("abc", "Int"), TypeError);
	assert.throws(() => toCanonicalFlexValue("invalid", "Currency"), TypeError);
	assert.throws(() => toCanonicalFlexValue("invalid_bool", "Check"), TypeError);
});

test("contract: normalizeConditionContract maps operator DTO array to ID lookup map", () => {
	const rawBackendContract = {
		api_version: "1",
		semantics_version: 1,
		node_types: {
			group: { required_keys: ["type", "operator", "children"] },
			comparison: { required_keys: ["type", "operator", "left"] },
			collection_predicate: { required_keys: ["type", "quantifier", "source", "as", "where"] },
		},
		flexvalue_modes: {
			static: ["string", "integer", "decimal", "boolean", "date", "datetime", "time", "list", "object", "null"],
			variable: { scopes: ["doc", "old_doc", "vars", "caller", "rule", "doctype"] },
			resolver: { families: [] },
			template: { segments: ["text", "value"], maximum_segments: 64 },
		},
		fieldtype_value_types: {
			Data: ["string"],
			Int: ["integer"],
			Currency: ["integer", "decimal"],
			Check: ["boolean"],
			Date: ["date"],
			Datetime: ["datetime"],
			Select: ["string"],
			Link: ["string"],
			"Dynamic Link": ["string"],
		},
		limits: { condition_depth: 8, condition_nodes: 64, path_segments: 6 },
		operators: [
			{
				id: "eq",
				label: "Equals",
				arity: 2,
				accepted_left_types: ["string", "decimal"],
				accepted_right_types: ["string", "decimal"],
			},
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
	assert.deepEqual(normalized.fieldtype_value_types.Currency, ["integer", "decimal"]);
	assert.equal(normalizeConditionContract({ api_version: "1", operators: [] }), null);
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

test("adapter: structured FlexValueControl membership models normalize to canonical lists", () => {
	for (const [fieldtype, operator, values] of [
		["Link", "in", ["Customer A", "Customer B"]],
		["Link", "not_in", ["Customer A", "Customer B", "Customer C"]],
		["Dynamic Link", "in", ["Doc A", "Doc B"]],
		["Select", "in", ["Open", "Closed"]],
	]) {
		const result = toCanonicalFlexValue(
			{ mode: "static", value_type: fieldtype, value: values },
			fieldtype,
			operator
		);
		assert.deepEqual(result, { mode: "static", value_type: "list", value: values });
	}
	const uiMultiSelect = toCanonicalFlexValue(
		{ mode: "static", value_type: "MultiSelectList", value: ["A", "B"] },
		"Link",
		"in"
	);
	assert.deepEqual(uiMultiSelect, { mode: "static", value_type: "list", value: ["A", "B"] });
	assert.throws(() => toCanonicalFlexValue({ mode: "static", value_type: "MultiSelectList", value: "A" }, "Link", "in"), TypeError);
});

test("adapter: incomplete drafts are omitted and unary operators serialize without right", () => {
	const incomplete = {
		id: "leaf-draft", type: "leaf", operator: "", left: null, right: null, is_incomplete_draft: true,
	};
	assert.equal(serializeConditionTree({ id: "root", type: "group", children: [incomplete] }), null);

	const unaryDraft = {
		id: "leaf-unary", type: "leaf", operator: "is_not_empty",
		left: { mode: "variable", path: { scope: "doc", segments: ["full_name"] } },
		right: null, is_incomplete_draft: true,
	};
	assert.deepEqual(serializeConditionTree({ id: "root", type: "group", children: [unaryDraft] }), {
		type: "comparison", operator: "is_not_empty",
		left: { mode: "variable", path: { scope: "doc", segments: ["full_name"] } },
	});
});

test("adapter: doctype variable source round-trips with no empty path segment", () => {
	const value = { mode: "variable", path: { scope: "doctype", segments: [] } };
	const result = toCanonicalFlexValue(value);
	assert.deepEqual(result, value);
});

test("adapter: sibling collection aliases are found in their actual lexical parent", () => {
	const tree = { id: "root", type: "group", children: [
		{ id: "root-group", type: "group", children: [
			{ id: "col-a", type: "collection", alias: "items_row", children: [] },
			{ id: "col-b", type: "collection", alias: "items_row_2", children: [] },
		] },
		{ id: "outer", type: "collection", alias: "orders_row", children: [
			{ id: "nested-group", type: "group", children: [
				{ id: "nested-a", type: "collection", alias: "lines_row", children: [] },
				{ id: "nested-b", type: "collection", alias: "lines_row_2", children: [] },
			] },
		] },
	] };
	assert.deepEqual(getCollectionSiblingAliases(tree, "col-a"), ["items_row_2"]);
	assert.deepEqual(getCollectionSiblingAliases(tree, "nested-a"), ["lines_row_2"]);
});

test("adapter: malformed stored JSON remains an unsupported, round-trippable value", () => {
	const malformed = '{"type":"comparison",';
	const tree = deserializeConditionTree(malformed);
	assert.equal(tree.children[0].is_unsupported, true);
	assert.equal(tree.children[0].original_payload, malformed);
	assert.equal(serializeConditionTree(tree), malformed);
});
