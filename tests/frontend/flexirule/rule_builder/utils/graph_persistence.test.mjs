import assert from "node:assert/strict";
import { test } from "node:test";
import {
	assertNoUnsupportedVisualOnlyNodes,
	formatVisualDataPayload,
	mergeVisualLayout,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/visual_layout.js";

test("formatVisualDataPayload excludes full node.data and action type/label for action nodes", () => {
	const nodes = [
		{
			id: "node-1",
			type: "process",
			label: "Action Label",
			position: { x: 100, y: 200 },
			direction: "LR",
			data: {
				action_id: "node-1",
				action_type: "Query Records",
				config: { secret: "do_not_duplicate" },
			},
		},
		{
			id: "annotation-1",
			type: "annotation",
			label: "Unsupported Annotation",
			is_visual_only: true,
			position: { x: 300, y: 400 },
			data: { text: "Not persisted by the current contract" },
		},
	];

	const edges = [
		{
			id: "e-node-1",
			source: "node-1",
			target: "node-2",
			sourceHandle: "default",
			targetHandle: null,
		},
		{
			id: "e-annotation",
			source: "annotation-1",
			target: "node-1",
			sourceHandle: "default",
			targetHandle: null,
		},
	];

	const payload = formatVisualDataPayload(nodes, edges, "LR", "LR");

	const actionPayloadNode = payload.find((item) => item.id === "node-1");
	assert.ok(actionPayloadNode, "action node present in payload");
	assert.equal(actionPayloadNode.data, undefined, "action data must not be duplicated");
	assert.equal(actionPayloadNode.type, undefined, "type is omitted for standard action node");
	assert.equal(actionPayloadNode.label, undefined, "label is omitted for standard action node");
	assert.deepEqual(actionPayloadNode.position, { x: 100, y: 200 });
	assert.equal(
		payload.some((item) => item.id === "annotation-1"),
		false,
		"standalone visual-only nodes are unsupported and not persisted"
	);
	assert.equal(
		payload.some((item) => item.source === "annotation-1" || item.target === "annotation-1"),
		false,
		"edges connected to unsupported visual-only nodes are not persisted"
	);

	const meta = payload.find((item) => item.type === "ui_preferences");
	assert.ok(meta, "ui_preferences meta included");
	assert.equal(meta.layout, "LR");
});

test("mergeVisualLayout updates positions without overwriting action data or resurrecting stale orphans", () => {
	const currentNodes = [
		{
			id: "action-1",
			type: "process",
			label: "Authoritative Action",
			position: { x: 0, y: 0 },
			data: {
				action_id: "action-1",
				action_type: "Assignment",
				config: { target: "new_value" },
			},
		},
	];
	const currentEdges = [];

	const visualData = [
		{
			id: "action-1",
			position: { x: 150, y: 250 },
			type: "process",
			label: "Old Stale Label",
			data: {
				action_type: "Assignment",
				config: { target: "OLD_STALE_VALUE" },
			},
		},
		{
			id: "deleted-orphan-action",
			position: { x: 500, y: 500 },
			type: "process",
			label: "Deleted Action",
			data: {
				action_type: "Query Records",
				config: { query: "secret" },
			},
		},
		{
			id: "orphan-visual-record",
			position: { x: 600, y: 600 },
			type: "annotation",
			label: "Annotation",
		},
	];

	const result = mergeVisualLayout(currentNodes, currentEdges, visualData);

	// 1. Position updated for action-1
	const actionNode = result.nodes.find((n) => n.id === "action-1");
	assert.ok(actionNode);
	assert.deepEqual(actionNode.position, { x: 150, y: 250 });
	// Action config and label MUST remain unchanged from doc.actions
	assert.equal(actionNode.data.config.target, "new_value");
	assert.equal(actionNode.label, "Authoritative Action");

	// 2. Deleted orphan action node and unknown visual orphan records MUST NOT be restored
	const orphanNode = result.nodes.find((n) => n.id === "deleted-orphan-action");
	assert.equal(orphanNode, undefined, "stale orphan action record must not be restored");

	const visualOrphan = result.nodes.find((n) => n.id === "orphan-visual-record");
	assert.equal(
		visualOrphan,
		undefined,
		"orphan visual record without doc.actions entry is ignored"
	);
});

test("assertNoUnsupportedVisualOnlyNodes rejects unsupported nodes before action serialization", () => {
	assert.doesNotThrow(() =>
		assertNoUnsupportedVisualOnlyNodes([
			{ id: "action-1", data: { action_type: "Assignment" } },
		])
	);
	assert.throws(
		() => assertNoUnsupportedVisualOnlyNodes([{ id: "annotation-1", is_visual_only: true }]),
		/Visual-only nodes.*not supported/
	);
});
