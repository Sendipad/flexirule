import test from "node:test";
import assert from "node:assert/strict";
import { resolveResolverOutputFieldtype } from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/resolver_output_fieldtype.mjs";

test("resolver output fieldtype uses Frappe-native Date, Datetime, and Time types", () => {
	const dynamicSpec = { output_type: "Date", output_type_is_dynamic: true };
	assert.equal(
		resolveResolverOutputFieldtype("date_time", "current", { token: "date" }, dynamicSpec),
		"Date"
	);
	assert.equal(
		resolveResolverOutputFieldtype("date_time", "current", { token: "datetime" }, dynamicSpec),
		"Datetime"
	);
	assert.equal(
		resolveResolverOutputFieldtype("date_time", "current", { token: "time" }, dynamicSpec),
		"Time"
	);
});

test("date_time.diff uses Int for whole units and Float for fractional units", () => {
	const dynamicSpec = { output_type: "Int", output_type_is_dynamic: true };
	for (const unit of ["days", "months", "years", "seconds"]) {
		assert.equal(resolveResolverOutputFieldtype("date_time", "diff", { diff_unit: unit }, dynamicSpec), "Int");
	}
	for (const unit of ["hours", "minutes"]) {
		assert.equal(resolveResolverOutputFieldtype("date_time", "diff", { diff_unit: unit }, dynamicSpec), "Float");
	}
});

test("date_time.calculate derives Date or Datetime only when the offset is knowable", () => {
	const dynamicSpec = { output_type: "Date", output_type_is_dynamic: true };
	const dateSource = { mode: "static", value_type: "Date", value: "2026-11-23" };
	assert.equal(
		resolveResolverOutputFieldtype(
			"date_time",
			"calculate",
			{ source: dateSource, offset_unit: "hours", offset_value: 0 },
			dynamicSpec
		),
		"Date"
	);
	assert.equal(
		resolveResolverOutputFieldtype(
			"date_time",
			"calculate",
			{ source: dateSource, offset_unit: "hours", offset_value: 2 },
			dynamicSpec
		),
		"Datetime"
	);
	assert.equal(
		resolveResolverOutputFieldtype(
			"date_time",
			"calculate",
			{
				source: dateSource,
				offset_unit: "hours",
				offset_value: { mode: "variable", path: { scope: "doc", segments: ["offset"] } },
			},
			dynamicSpec
		),
		null
	);
});

test("system role checks use Frappe Check fieldtype", () => {
	const dynamicSpec = { output_type: "Data", output_type_is_dynamic: true };
	assert.equal(
		resolveResolverOutputFieldtype(
			"system_context",
			"get",
			{ sys_token: "role_check", sys_role: "System Manager" },
			dynamicSpec
		),
		"Check"
	);
});
