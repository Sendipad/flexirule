import assert from "node:assert/strict";
import { test } from "node:test";
import { createWorkspaceShowPageGuard } from "../../../../../flexirule/public/js/flexirule/utils/workspace_page_guard.js";

function makeWorkspace(overrides = {}) {
	return {
		all_pages: [{ title: "Build" }, { title: "Private Reports" }],
		public_pages: [{ title: "Build" }],
		private_pages: [{ title: "Private Reports" }],
		...overrides,
	};
}

test("a legitimate workspace page invokes the original method with the same context and arguments", async () => {
	const workspace = makeWorkspace();
	const page = { name: "Build", public: true };
	let received;
	const originalResult = { rendered: true };
	const guarded = createWorkspaceShowPageGuard(function (receivedPage, extraArg) {
		received = { context: this, args: [receivedPage, extraArg] };
		return Promise.resolve(originalResult);
	});

	const result = await guarded.call(workspace, page, "extra");

	assert.equal(result, originalResult);
	assert.equal(received.context, workspace);
	assert.deepEqual(received.args, [page, "extra"]);
});

test("a legitimate private workspace page still delegates to Frappe", async () => {
	const workspace = makeWorkspace();
	const page = { name: "Private Reports", public: false };
	let receivedPage;
	const guarded = createWorkspaceShowPageGuard(function (requestedPage) {
		receivedPage = requestedPage;
		return "private-page-rendered";
	});

	assert.equal(await guarded.call(workspace, page), "private-page-rendered");
	assert.equal(receivedPage, page);
});

test("a loaded workspace skips an unrelated route before Frappe dereferences a missing page", async () => {
	const workspace = makeWorkspace();
	let originalCalls = 0;
	const originalRouterError = new TypeError(
		"Cannot read properties of undefined (reading 'name')"
	);
	const guarded = createWorkspaceShowPageGuard(() => {
		originalCalls += 1;
		throw originalRouterError;
	});

	await assert.doesNotReject(() =>
		guarded.call(workspace, { name: "rule-builder", public: true })
	);
	assert.equal(
		originalCalls,
		0,
		"the original failing lookup must not run for a missing workspace page"
	);
});

test("the guard delegates when workspace data is not loaded", async () => {
	const workspace = makeWorkspace({ all_pages: [] });
	let originalCalls = 0;
	const guarded = createWorkspaceShowPageGuard(() => {
		originalCalls += 1;
		return "delegated";
	});

	assert.equal(
		await guarded.call(workspace, { name: "rule-builder", public: true }),
		"delegated"
	);
	assert.equal(originalCalls, 1);
});

test("the guard does not swallow unrelated errors from the original implementation", async () => {
	const workspace = makeWorkspace();
	const unrelatedError = new Error("unrelated workspace rendering failure");
	const guarded = createWorkspaceShowPageGuard(() => {
		throw unrelatedError;
	});

	await assert.rejects(
		guarded.call(workspace, { name: "Build", public: true }),
		(error) => error === unrelatedError
	);
});

test("malformed page-list state is delegated rather than silently suppressed", async () => {
	const workspace = makeWorkspace({ public_pages: null });
	let originalCalls = 0;
	const unrelatedError = new Error("unexpected Frappe state error");
	const guarded = createWorkspaceShowPageGuard(() => {
		originalCalls += 1;
		throw unrelatedError;
	});

	await assert.rejects(
		guarded.call(workspace, { name: "rule-builder", public: true }),
		(error) => error === unrelatedError
	);
	assert.equal(originalCalls, 1);
});

test("the guard requires a valid original method", () => {
	assert.throws(
		() => createWorkspaceShowPageGuard(null),
		/Workspace\.show_page must be a function/
	);
});
