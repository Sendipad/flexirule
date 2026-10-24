import assert from "node:assert/strict";
import { stableStringify } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/stable_serialization.mjs";

// Object insertion order must not affect dirty comparisons, including nested config.
assert.equal(
	stableStringify({ config: { limit: 20, fields: ["name"] }, action_type: "Query Records" }),
	stableStringify({ action_type: "Query Records", config: { fields: ["name"], limit: 20 } })
);

// Semantic changes remain observable.
assert.notEqual(
	stableStringify({ config: { limit: 20 } }),
	stableStringify({ config: { limit: 21 } })
);
assert.notEqual(
	stableStringify({ fields: ["name", "customer"] }),
	stableStringify({ fields: ["customer", "name"] })
);

// Match JSON behavior for omitted object properties and undefined array entries.
assert.equal(stableStringify({ present: 1, omitted: undefined }), '{"present":1}');
assert.equal(stableStringify([1, undefined, 3]), "[1,null,3]");
const sparse = [];
sparse[1] = "value";
assert.equal(stableStringify(sparse), '[null,"value"]');
assert.equal(stableStringify([() => {}, Symbol("ignored")]), "[null,null]");
assert.equal(stableStringify(undefined), undefined);
assert.equal(
	stableStringify({ date: new Date("2026-01-02T03:04:05.000Z") }),
	'{"date":"2026-01-02T03:04:05.000Z"}'
);

// Cycles fail explicitly instead of recursing indefinitely.
const cyclic = {};
cyclic.self = cyclic;
assert.throws(() => stableStringify(cyclic), TypeError);
const selfReturningToJSON = {
	toJSON() {
		return this;
	},
};
assert.equal(stableStringify(selfReturningToJSON), JSON.stringify(selfReturningToJSON));
assert.equal(
	stableStringify(selfReturningToJSON),
	"{}",
	"A self-returning toJSON method should be invoked once and then serialize enumerable data."
);
let toJSONCalls = 0;
assert.equal(
	stableStringify({
		toJSON() {
			toJSONCalls += 1;
			return { nested: { value: 1 } };
		},
	}),
	'{"nested":{"value":1}}'
);
assert.equal(toJSONCalls, 1, "toJSON must be called once for the current property.");

// Repeated shared objects are valid when the object graph is not cyclic.
const shared = { value: 1 };
assert.equal(
	stableStringify({ left: shared, right: shared }),
	'{"left":{"value":1},"right":{"value":1}}'
);

console.log("stable serialization tests passed");
