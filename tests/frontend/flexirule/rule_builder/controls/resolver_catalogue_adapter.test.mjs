import test from "node:test";
import assert from "node:assert/strict";
import {
	normalizeStrategyDefaultState,
	adaptStrategiesForCatalogue,
	getCanonicalFamilyForKind,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/resolver_catalogue_adapter.mjs";

test("resolver_catalogue_adapter: normalizes real strategy kinds and operations", () => {
	// Date & Time
	const dtState = {
		operation: "calculate",
		config: { token: "date", offset_unit: "days" },
	};
	const dtNorm = normalizeStrategyDefaultState("date_time", dtState);
	assert.equal(dtNorm.family, "date_time");
	assert.equal(dtNorm.operation, "calculate");
	assert.equal(dtNorm.config.token, "date");

	// Text
	const textState = {
		operation: "combine",
		config: { str_a_type: "field" },
	};
	const textNorm = normalizeStrategyDefaultState("text", textState);
	assert.equal(textNorm.family, "text");
	assert.equal(textNorm.operation, "combine");

	// Collection
	const colState = {
		source: "doc.items",
		operation: "any",
		target_field: "",
	};
	const colNorm = normalizeStrategyDefaultState("collection", colState);
	assert.equal(colNorm.family, "collection");
	assert.equal(colNorm.operation, "any");

	// Math Formula
	const mathState = {
		field_a: "doc.qty",
		math_op: "*",
		constant_b: 2,
	};
	const mathNorm = normalizeStrategyDefaultState("math_formula", mathState);
	assert.equal(mathNorm.family, "math");
	assert.equal(mathNorm.operation, "formula");
	assert.equal(mathNorm.config.math_op, "*");

	// Lookup
	const lookupState = {
		doctype_mode: "static",
		target_doctype: "Customer",
	};
	const lookupNorm = normalizeStrategyDefaultState("lookup", lookupState);
	assert.equal(lookupNorm.family, "lookup");
	assert.equal(lookupNorm.operation, "fetch");

	// System Context
	const sysState = {
		sys_token: "user",
	};
	const sysNorm = normalizeStrategyDefaultState("system_context", sysState);
	assert.equal(sysNorm.family, "system_context");
	assert.equal(sysNorm.operation, "get");
});

test("resolver_catalogue_adapter: adaptStrategiesForCatalogue calls defaultState and produces catalogue items", () => {
	const mockStrategies = [
		{
			kind: "date_time",
			label: "Date & Time",
			defaultState: (props) => ({
				operation: "calculate",
				config: { token: "date" },
			}),
		},
		{
			kind: "math_formula",
			label: "Math Formula",
			defaultState: () => ({
				field_a: "",
				math_op: "+",
			}),
		},
	];

	const adapted = adaptStrategiesForCatalogue(mockStrategies, {});
	assert.equal(adapted.length, 2);
	assert.equal(adapted[0].kind, "date_time");
	assert.equal(adapted[0].family, "date_time");
	assert.equal(adapted[0].operation, "calculate");
	assert.equal(adapted[0].defaultConfig.config.token, "date");

	assert.equal(adapted[1].kind, "math_formula");
	assert.equal(adapted[1].family, "math");
	assert.equal(adapted[1].operation, "formula");
	assert.equal(adapted[1].defaultConfig.config.math_op, "+");
});
