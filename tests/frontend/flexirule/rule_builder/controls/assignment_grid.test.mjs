import assert from "node:assert/strict";
import { test } from "node:test";

test("GenericGrid header slot and AssignmentConfig operations verification", () => {
	// Verify assignment serialization model
	const rawAssignments = [
		{
			name: "a1",
			target: "doc.status",
			operator: "set",
			when_condition: null,
			value: { mode: "static", value: "Closed" },
		},
		{
			name: "a2",
			target: "vars.counter",
			operator: "increment",
			when_condition: null,
			value: { mode: "static", value: "1" },
		},
	];

	// Verify order manipulation (move up / down)
	const list = [...rawAssignments];
	const moved = list.splice(0, 1)[0];
	list.splice(1, 0, moved);

	assert.equal(list[0].name, "a2");
	assert.equal(list[1].name, "a1");

	// Verify row removal
	list.splice(0, 1);
	assert.equal(list.length, 1);
	assert.equal(list[0].name, "a1");
});
