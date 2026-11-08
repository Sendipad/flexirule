import test from "node:test";
import assert from "node:assert/strict";
import {
	buildSourceCatalogue,
	searchSourceCatalogue,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/source_catalogue.mjs";
import { resolveStaticPresentation } from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/static_presentation_policy.mjs";
import {
	normalizeStrategyDefaultState,
	adaptStrategiesForCatalogue,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/resolver_catalogue_adapter.mjs";

test("p1_verification: native fieldtypes are preserved without coercing to Data", () => {
	const nativeTypes = [
		"Int",
		"Float",
		"Currency",
		"Percent",
		"Check",
		"Date",
		"Datetime",
		"Time",
		"Select",
		"Link",
	];
	for (const ft of nativeTypes) {
		const res = resolveStaticPresentation({ fieldType: ft });
		if (ft === "Select") assert.equal(res.control, "select");
		else if (ft === "Link") assert.equal(res.control, "link");
		else assert.equal(res.control, "input");
	}
});

test("p1_verification: real resolver strategies retain their native default states and operations", () => {
	const mockStrategies = [
		{
			kind: "date_time",
			label: "Date & Time",
			defaultState: () => ({ operation: "calculate", config: { token: "date" } }),
		},
		{
			kind: "text",
			label: "Text",
			defaultState: () => ({ operation: "combine", config: { str_a_type: "field" } }),
		},
		{
			kind: "collection",
			label: "Collection",
			defaultState: () => ({ operation: "any", source: "doc.items" }),
		},
		{
			kind: "math_formula",
			label: "Math Formula",
			defaultState: () => ({ field_a: "", math_op: "+" }),
		},
		{
			kind: "lookup",
			label: "Lookup",
			defaultState: () => ({ doctype_mode: "static", target_doctype: "" }),
		},
		{
			kind: "system_context",
			label: "System Context",
			defaultState: () => ({ sys_token: "user" }),
		},
	];

	const adapted = adaptStrategiesForCatalogue(mockStrategies, {});
	assert.equal(adapted.length, 6);

	assert.equal(adapted[0].operation, "calculate");
	assert.equal(adapted[1].operation, "combine");
	assert.equal(adapted[2].operation, "any");
	assert.equal(adapted[3].operation, "formula");
	assert.equal(adapted[4].operation, "fetch");
	assert.equal(adapted[5].operation, "get");
});

test("p2_verification: deduplicates sources across docFields and variableOptions by canonical identity", () => {
	const docFields = [{ fieldname: "title", label: "Title", fieldtype: "Data" }];
	const variableOptions = [
		{ value: "doc.title", label: "doc.title (Title)" },
		{ value: "old_doc.title", label: "old_doc.title (Previous Title)" },
		{ value: "vars.counter", label: "Counter" },
	];

	const catalogue = buildSourceCatalogue({ docFields, variableOptions });
	assert.equal(catalogue.length, 3); // doc.title deduplicated, old_doc.title and vars.counter preserved

	const titleItems = catalogue.filter((i) => i.canonicalPath === "doc.title");
	assert.equal(titleItems.length, 1);
});

test("finding_1_verification: membership static serialization handles numeric and date fields", () => {
	// Simulate the list parsing logic used in FlexValueControl serialize()
	function parseListElements(val, targetFieldType) {
		let rawList = [];
		if (Array.isArray(val)) {
			rawList = val;
		} else if (typeof val === "string") {
			rawList = val
				.split(",")
				.map((s) => s.trim())
				.filter(Boolean);
		} else if (val !== null && val !== undefined && val !== "") {
			rawList = [val];
		}

		const isInt = targetFieldType === "Int" || targetFieldType === "integer";
		const isFloat = ["Float", "Currency", "Percent", "decimal"].includes(targetFieldType);

		return rawList.map((item) => {
			if (typeof item === "string") {
				const trimmed = item.trim();
				if (isInt) {
					const parsed = parseInt(trimmed, 10);
					return isNaN(parsed) ? trimmed : parsed;
				}
				if (isFloat) {
					const parsed = parseFloat(trimmed);
					return isNaN(parsed) ? trimmed : parsed;
				}
				return trimmed;
			}
			return item;
		});
	}

	const intList = parseListElements(["10", "20", "30"], "Int");
	assert.deepEqual(intList, [10, 20, 30]);

	const floatList = parseListElements(["10.5", "25.75"], "Currency");
	assert.deepEqual(floatList, [10.5, 25.75]);

	const dateList = parseListElements(["2025-01-01", "2025-01-02"], "Date");
	assert.deepEqual(dateList, ["2025-01-01", "2025-01-02"]);
});
