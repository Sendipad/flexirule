import assert from "node:assert/strict";
import { test } from "node:test";
import { guardWorkspaceShowPage } from "../../../../flexirule/public/js/flexirule/utils/workspace_page_guard.js";

test("valid workspace page delegates to the original method with its context and arguments", async () => {
	const calls = [];
	const originalError = null;
	const originalShowPage = async function (page, extra) {
		calls.push({ context: this, page, extra });
		return { rendered: page.name, extra };
	};
	const context = {
		all_pages: [{ title: "Home" }, { title: "FlexiRule" }],
		public_pages: [{ title: "Home", content: "[]" }],
		private_pages: [{ title: "FlexiRule", content: "[]" }],
	};
	const page = { name: "FlexiRule", public: false };

	const result = await guardWorkspaceShowPage(originalShowPage).call(
		context,
		page,
		"sentinel"
	);

	assert.deepEqual(result, { rendered: "FlexiRule", extra: "sentinel" });
	assert.equal(calls.length, 1);
	assert.equal(calls[0].context, context);
	assert.equal(calls[0].page, page);
	assert.equal(calls[0].extra, "sentinel");
	assert.equal(originalError, null);
});

test("invalid route in an initialized workspace skips the crashing original lookup", async () => {
	let originalCalled = false;
	const originalShowPage = async function () {
		originalCalled = true;
		throw new TypeError("Cannot read properties of undefined (reading 'name')");
	};
	const context = {
		all_pages: [{ title: "Home" }],
		public_pages: [{ title: "Home", content: "[]" }],
		private_pages: [{ title: "Home", content: "[]" }],
	};

	const result = await guardWorkspaceShowPage(originalShowPage).call(context, {
		name: "Not a Workspace",
		public: false,
	});

	assert.equal(result, undefined);
	assert.equal(originalCalled, false);
});

test("a public workspace page uses the public page list and still delegates", async () => {
	let receivedPage;
	const originalShowPage = async function (page) {
		receivedPage = page;
		return "rendered";
	};
	const context = {
		all_pages: [{ title: "Public Home" }, { title: "Private Home" }],
		public_pages: [{ title: "Public Home", content: "[]" }],
		private_pages: [{ title: "Private Home", content: "[]" }],
	};
	const page = { name: "Public Home", public: true };

	assert.equal(
		await guardWorkspaceShowPage(originalShowPage).call(context, page),
		"rendered"
	);
	assert.equal(receivedPage, page);
});

test("uninitialized workspace lists preserve the original method's behavior", async () => {
	let called = false;
	const originalShowPage = async function (page) {
		called = true;
		return page.name;
	};

	const result = await guardWorkspaceShowPage(originalShowPage).call(
		{ all_pages: [], public_pages: [], private_pages: [] },
		{ name: "Home", public: true }
	);

	assert.equal(called, true);
	assert.equal(result, "Home");
});

test("unrelated errors from the original renderer propagate unchanged", async () => {
	const renderError = new Error("Unexpected error while rendering a valid page");
	const originalShowPage = async function () {
		throw renderError;
	};
	const context = {
		all_pages: [{ title: "Home" }],
		public_pages: [],
		private_pages: [{ title: "Home", content: "[]" }],
	};

	await assert.rejects(
		guardWorkspaceShowPage(originalShowPage).call(context, {
			name: "Home",
			public: false,
		}),
		(error) => error === renderError
	);
});

test("an absent page argument is ignored without calling the original method", async () => {
	let called = false;
	const originalShowPage = async function () {
		called = true;
	};

	assert.equal(await guardWorkspaceShowPage(originalShowPage).call({ all_pages: [] }), undefined);
	assert.equal(called, false);
});
