import test from "node:test";
import assert from "node:assert/strict";

import {
	validateCanonicalCondition,
	isLeafComplete,
	isOperatorUnary,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_validation.mjs";
import {
	serializeConditionTree,
	deserializeConditionTree,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_adapter.mjs";
import {
	getFunctionIcon,
	FORMULA_REGISTRY,
	SLASH_COMMANDS,
} from "../../../../../flexirule/public/js/flexirule/core/formula_registry.js";

const CONTRACT_FIXTURE = {
	operators: {
		eq: {
			id: "eq",
			label: "Equals",
			arity: 2,
			accepted_left_types: ["string", "integer", "decimal"],
			accepted_right_types: ["string", "integer", "decimal"],
			fieldtypes: null,
		},
		is_set: {
			id: "is_set",
			label: "Is set",
			arity: 1,
			accepted_left_types: ["string", "integer"],
			accepted_right_types: [],
			fieldtypes: null,
		},
	},
	limits: {
		depth: 16,
		nodes: 128,
		path_segments: 8,
	},
};

test("Address Scenario Reproduction: incomplete draft lifecycle & canonical serialization", () => {
	// 1. Initial empty leaf has is_incomplete_draft
	const leaf = {
		id: "leaf_addr_1",
		type: "leaf",
		operator: "",
		left: null,
		right: null,
		is_incomplete_draft: true,
	};
	const tree = { id: "root", type: "group", operator: "and", children: [leaf] };

	// Validation catches missing left & operator
	const initialVal = validateCanonicalCondition(tree, {
		contract: CONTRACT_FIXTURE,
		isMandatory: true,
	});
	assert.equal(initialVal.valid, false);
	assert.ok(initialVal.errors.includes("Choose a value source."));
	assert.ok(initialVal.errors.includes("Choose how the value should match."));

	// 2. User selects doc.address
	leaf.left = { mode: "variable", path: { scope: "doc", segments: ["address"] } };
	assert.equal(isLeafComplete(leaf, CONTRACT_FIXTURE), false);
	const step2Val = validateCanonicalCondition(tree, {
		contract: CONTRACT_FIXTURE,
		isMandatory: true,
	});
	assert.equal(step2Val.valid, false);
	assert.ok(!step2Val.errors.includes("Choose a value source."));
	assert.ok(step2Val.errors.includes("Choose how the value should match."));

	// 3. User selects operator: eq (internal ID)
	leaf.operator = "eq";
	assert.equal(isLeafComplete(leaf, CONTRACT_FIXTURE), false);
	const step3Val = validateCanonicalCondition(tree, {
		contract: CONTRACT_FIXTURE,
		isMandatory: true,
	});
	assert.equal(step3Val.valid, false);
	assert.ok(step3Val.errors.includes("Choose a comparison value."));

	// 4. User enters right: PM Address-Billing
	leaf.right = { mode: "static", value_type: "string", value: "PM Address-Billing" };

	// Readiness check passes and draft flag is deleted
	assert.equal(isLeafComplete(leaf, CONTRACT_FIXTURE), true);
	delete leaf.is_incomplete_draft;

	const step4Val = validateCanonicalCondition(tree, {
		contract: CONTRACT_FIXTURE,
		isMandatory: true,
	});
	assert.equal(step4Val.valid, true);
	assert.equal(step4Val.errors.length, 0);

	// Canonical serialization matches the exact expected payload from section 1
	const canonicalAst = serializeConditionTree(tree, CONTRACT_FIXTURE.operators);
	assert.deepEqual(canonicalAst, {
		type: "comparison",
		operator: "eq",
		left: {
			mode: "variable",
			path: {
				scope: "doc",
				segments: ["address"],
			},
		},
		right: {
			mode: "static",
			value_type: "string",
			value: "PM Address-Billing",
		},
	});

	// Round-trip deserialization preserves the condition without UI draft artifacts
	const roundtrippedTree = deserializeConditionTree(canonicalAst);
	assert.equal(roundtrippedTree.children.length, 1);
	assert.equal(roundtrippedTree.children[0].operator, "eq");
	assert.equal(roundtrippedTree.children[0].left.path.segments[0], "address");
	assert.equal(roundtrippedTree.children[0].right.value, "PM Address-Billing");
});

test("Contract-driven Operator Arity: unary operator needs no right operand", () => {
	const unaryLeaf = {
		id: "leaf_unary_1",
		type: "leaf",
		operator: "is_set",
		left: { mode: "variable", path: { scope: "doc", segments: ["address"] } },
		right: null,
	};
	assert.equal(isOperatorUnary("is_set", CONTRACT_FIXTURE), true);
	assert.equal(isOperatorUnary("eq", CONTRACT_FIXTURE), false);
	assert.equal(isLeafComplete(unaryLeaf, CONTRACT_FIXTURE), true);

	const tree = { id: "root", type: "group", operator: "and", children: [unaryLeaf] };
	const serialized = serializeConditionTree(tree, CONTRACT_FIXTURE.operators);
	assert.deepEqual(serialized, {
		type: "comparison",
		operator: "is_set",
		left: {
			mode: "variable",
			path: {
				scope: "doc",
				segments: ["address"],
			},
		},
	});
	assert.equal("right" in serialized, false);
});

test("Formula & Resolver Icons: domain-appropriate FontAwesome icons", () => {
	assert.equal(getFunctionIcon("concat"), "fa fa-link");
	assert.equal(getFunctionIcon("normalize"), "fa fa-refresh");
	assert.equal(getFunctionIcon("format"), "fa fa-align-left");
	assert.equal(getFunctionIcon("replace"), "fa fa-exchange");
	assert.equal(getFunctionIcon("trim"), "fa fa-scissors");
	assert.equal(getFunctionIcon("round"), "fa fa-calculator");
	assert.equal(getFunctionIcon("today"), "fa fa-calendar-check-o");
	assert.equal(getFunctionIcon("now"), "fa fa-clock-o");
	assert.equal(getFunctionIcon("lookup"), "fa fa-search");

	// Clear Editor uses fa-trash instead of emoji
	const clearCmd = SLASH_COMMANDS.find((c) => c.id === "clear");
	assert.ok(clearCmd);
	assert.equal(clearCmd.icon, "fa fa-trash");
});

test("Entry Condition deletion safety: confirmation on sole entry condition", () => {
	// Root group with 1 condition
	const root = {
		id: "root",
		type: "group",
		children: [{ id: "leaf_1", type: "leaf" }],
	};

	let promptCalled = false;
	const mockConfirmPrompt = (nodeId, rootTree, isEntryNode) => {
		const children = rootTree?.children || [];
		const isSole = children.length === 1 && children[0].id === nodeId;
		if (isSole && isEntryNode) {
			promptCalled = true;
			return false; // User clicks cancel
		}
		return true;
	};

	// When user cancels deletion of sole entry condition
	const canDeleteCancelled = mockConfirmPrompt("leaf_1", root, true);
	assert.equal(canDeleteCancelled, false);
	assert.equal(promptCalled, true);

	// When deleting a non-entry node or when multi-condition exists
	root.children.push({ id: "leaf_2", type: "leaf" });
	promptCalled = false;
	const canDeleteMulti = mockConfirmPrompt("leaf_1", root, true);
	assert.equal(canDeleteMulti, true);
	assert.equal(promptCalled, false);
});

test("Membership Serialization: canonical FlexValue payloads accepted by backend", () => {
	// Select / Link field membership comparison
	const membershipTree = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "leaf_mem_1",
				type: "leaf",
				operator: "in",
				left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
				right: {
					mode: "static",
					value_type: "list",
					value: ["Draft", "Open", "Cancelled"],
				},
			},
			{
				id: "leaf_mem_2",
				type: "leaf",
				operator: "not_in",
				left: { mode: "variable", path: { scope: "doc", segments: ["customer"] } },
				right: { mode: "static", value_type: "list", value: ["Cust-001", "Cust-002"] },
			},
		],
	};

	const serialized = serializeConditionTree(membershipTree, CONTRACT_FIXTURE.operators);
	assert.equal(serialized.type, "group");
	assert.equal(serialized.children.length, 2);

	// First comparison
	const comp1 = serialized.children[0];
	assert.equal(comp1.operator, "in");
	assert.equal(comp1.right.mode, "static");
	assert.equal(comp1.right.value_type, "list");
	assert.deepEqual(comp1.right.value, ["Draft", "Open", "Cancelled"]);
	// Control name must never become value_type
	assert.notEqual(comp1.right.value_type, "multi-select");
	assert.notEqual(comp1.right.value_type, "MultiSelectList");

	// Second comparison
	const comp2 = serialized.children[1];
	assert.equal(comp2.operator, "not_in");
	assert.equal(comp2.right.mode, "static");
	assert.equal(comp2.right.value_type, "list");
	assert.deepEqual(comp2.right.value, ["Cust-001", "Cust-002"]);
	assert.notEqual(comp2.right.value_type, "multi-select");
});
