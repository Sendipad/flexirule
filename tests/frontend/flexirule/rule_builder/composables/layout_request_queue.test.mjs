import assert from "node:assert/strict";
import { test } from "node:test";

import { createLatestRequestQueue } from "../../../../../flexirule/public/js/flexirule/rule_builder/composables/layout_request_queue.mjs";

function createDeferred() {
	let resolve;
	let reject;
	const promise = new Promise((resolvePromise, rejectPromise) => {
		resolve = resolvePromise;
		reject = rejectPromise;
	});
	return { promise, resolve, reject };
}

test("serializes active work and coalesces pending requests to the latest task", async () => {
	const enqueue = createLatestRequestQueue();
	const gate = createDeferred();
	const started = [];

	const active = enqueue(async () => {
		started.push("active");
		await gate.promise;
		return "active-result";
	});
	const superseded = enqueue(async () => {
		started.push("superseded");
		return "superseded-result";
	});
	const latest = enqueue(async () => {
		started.push("latest");
		return "latest-result";
	});

	assert.deepEqual(started, ["active"]);
	gate.resolve();

	assert.equal(await active, "active-result");
	assert.equal(await superseded, "latest-result");
	assert.equal(await latest, "latest-result");
	assert.deepEqual(started, ["active", "latest"]);
});

test("continues draining queued work after a task rejects", async () => {
	const enqueue = createLatestRequestQueue();
	const gate = createDeferred();
	const started = [];

	const failing = enqueue(async () => {
		started.push("failing");
		await gate.promise;
		throw new Error("expected layout failure");
	});
	const recovery = enqueue(async () => {
		started.push("recovery");
		return "recovered";
	});

	gate.resolve();
	await assert.rejects(failing, /expected layout failure/);
	assert.equal(await recovery, "recovered");
	assert.deepEqual(started, ["failing", "recovery"]);
});

test("rejects non-function requests without poisoning the queue", async () => {
	const enqueue = createLatestRequestQueue();

	await assert.rejects(enqueue(null), /must be a function/);
	assert.equal(await enqueue(() => "healthy"), "healthy");
});
