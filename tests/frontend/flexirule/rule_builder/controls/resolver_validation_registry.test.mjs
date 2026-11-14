import test from "node:test";
import assert from "node:assert/strict";
import { createResolverValidationRegistry } from "../../../../flexirule/public/js/flexirule/rule_builder/controls/resolver_validation_registry.mjs";

test("nested resolver validation is awaited and propagated to the owner", async () => {
	const registry = createResolverValidationRegistry();
	let validated = false;
	registry.register(async () => {
		await Promise.resolve();
		validated = true;
		return { valid: false, errors: ["Collection filter is invalid."] };
	});

	const result = await registry.validate();
	assert.equal(validated, true);
	assert.equal(result.valid, false);
	assert.deepEqual(result.errors, ["Collection filter is invalid."]);
});

test("unmounted resolver validators are removed", async () => {
	const registry = createResolverValidationRegistry();
	const unregister = registry.register(() => ({ valid: false, errors: ["stale"] }));
	unregister();
	assert.deepEqual(await registry.validate(), { valid: true, errors: [] });
});

test("resolver validation exceptions fail closed", async () => {
	const registry = createResolverValidationRegistry();
	registry.register(() => {
		throw new Error("nested validation unavailable");
	});
	assert.deepEqual(await registry.validate(), {
		valid: false,
		errors: ["nested validation unavailable"],
	});
});
