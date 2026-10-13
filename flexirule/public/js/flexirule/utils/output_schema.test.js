import assert from "node:assert/strict";
import {
	hasConfiguredResolvedOutputSchema,
	normalizeResolvedOutputSchema,
} from "./output_schema.js";

assert.equal(hasConfiguredResolvedOutputSchema(null), false);
assert.equal(hasConfiguredResolvedOutputSchema(""), false);
assert.equal(hasConfiguredResolvedOutputSchema([]), false);
assert.equal(hasConfiguredResolvedOutputSchema("[]"), false);
assert.equal(hasConfiguredResolvedOutputSchema("  []  "), false);
assert.equal(hasConfiguredResolvedOutputSchema('[{"fieldname":"name"}]'), true);
assert.equal(hasConfiguredResolvedOutputSchema([{ fieldname: "name" }]), true);
assert.equal(hasConfiguredResolvedOutputSchema("{"), true);

// Keep the editor's canonical empty value while treating it as absent at save time.
assert.deepEqual(normalizeResolvedOutputSchema(null), []);
console.log("output schema contract tests passed");
