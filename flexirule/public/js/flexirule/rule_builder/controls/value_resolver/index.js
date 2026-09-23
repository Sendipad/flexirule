import ValueSourceResolver from "./components/ValueSourceResolver.vue";
import DateResolver from "./components/DateResolver.vue";
import TextResolver from "./components/TextResolver.vue";
import MathResolver from "./components/MathResolver.vue";
import CollectionResolver from "./components/CollectionResolver.vue";
import AggregateResolver from "./components/AggregateResolver.vue";
import LookupResolver from "./components/LookupResolver.vue";
import ConditionalResolver from "./components/ConditionalResolver.vue";
import TypeConversionResolver from "./components/TypeConversionResolver.vue";

import { registerStrategy } from "./strategies";
import { __, toDocExpression, validateField } from "./utils";
import { useStore } from "../../stores";

// ─── 1. Value Source Strategy ───
registerStrategy("value_source", {
	label: __("Value Source"),
	description: __("Select document field, rule variable, static primitive, or system context token."),
	icon: "fa fa-database",
	component: ValueSourceResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		let path = "";
		if (fieldname) path = String(fieldname).replace(/^(doc|vars)\./, "");
		return { operation: "field", path, value: "", sys_token: "user", sys_role: "" };
	},
	compileToCode: (item) => {
		if (item.operation === "static") return `"${item.value || ""}"`;
		if (item.operation === "system_context") {
			return item.sys_token === "role_check"
				? `{"${item.sys_role}" in frappe.get_roles(frappe.session.user)}`
				: "{frappe.session.user}";
		}
		return item.path ? `{${toDocExpression(item.path)}}` : '""';
	},
	compileToLabel: (item) => {
		if (item.operation === "static") return `Static: "${item.value || ""}"`;
		if (item.operation === "system_context") {
			return item.sys_token === "user" ? __("User ID") : `Role: ${item.sys_role}`;
		}
		return `${item.operation === "variable" ? "Var" : "Field"}: ${item.path || "?"}`;
	},
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 2. Date Strategy ───
registerStrategy("date", {
	label: __("Date"),
	description: __("Calculate date offsets (+/- days/months/years) or date differences."),
	icon: "fa fa-calendar",
	component: DateResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		let baseField = fieldname ? String(fieldname).replace(/^(doc|vars)\./, "") : "";
		return {
			operation: "add",
			base_type: baseField ? "doc_field" : "today",
			base_field: baseField,
			offset_value: 0,
			offset_unit: "days",
			diff_start_type: "today",
			diff_start_field: "",
			diff_end_type: "doc_field",
			diff_end_field: "",
			diff_unit: "days",
		};
	},
	compileToCode: (item) => {
		if (item.operation === "diff") {
			const start = item.diff_start_type === "today" ? "frappe.utils.nowdate()" : toDocExpression(item.diff_start_field);
			const end = item.diff_end_type === "today" ? "frappe.utils.nowdate()" : toDocExpression(item.diff_end_field);
			if (item.diff_unit === "days") return `{frappe.utils.date_diff(${end}, ${start})}`;
			if (item.diff_unit === "months") return `{frappe.utils.month_diff(${end}, ${start})}`;
			return `{int(frappe.utils.month_diff(${end}, ${start}) / 12)}`;
		}
		const baseExpr = item.base_type === "today" ? "frappe.utils.nowdate()" : toDocExpression(item.base_field);
		let offset = parseInt(item.offset_value || 0, 10);
		if (item.operation === "subtract" && offset > 0) offset = -offset;
		if (offset === 0 || !item.offset_unit) return `{${baseExpr}}`;
		if (item.offset_unit === "days") return `{frappe.utils.add_days(${baseExpr}, ${offset})}`;
		return `{frappe.utils.add_to_date(${baseExpr}, ${item.offset_unit}=${offset})}`;
	},
	compileToLabel: (item) => {
		if (item.operation === "diff") {
			const start = item.diff_start_type === "today" ? __("Today") : item.diff_start_field || "?";
			const end = item.diff_end_type === "today" ? __("Today") : item.diff_end_field || "?";
			return `${end} − ${start} (${item.diff_unit})`;
		}
		const base = item.base_type === "today" ? __("Today") : item.base_field || __("Field");
		const offset = parseInt(item.offset_value || 0, 10);
		const sign = item.operation === "subtract" ? "-" : "+";
		return `Date: ${base} ${sign}${offset} ${item.offset_unit}`;
	},
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 3. Text Strategy ───
registerStrategy("text", {
	label: __("Text"),
	description: __("Manipulate text: concatenate, trim, casing, replacement, currency, date formatting."),
	icon: "fa fa-font",
	component: TextResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		return {
			operation: "concat",
			field_a: fieldname ? String(fieldname).replace(/^(doc|vars)\./, "") : "",
			field_b: "",
			fmt_config: "",
		};
	},
	compileToCode: (item) => {
		const a = toDocExpression(item.field_a || '""');
		const b = toDocExpression(item.field_b || '""');
		if (item.operation === "concat") return `{str(${a} or "") + str(${b} or "")}`;
		if (item.operation === "upper") return `{str(${a} or "").upper()}`;
		if (item.operation === "lower") return `{str(${a} or "").lower()}`;
		if (item.operation === "trim") return `{str(${a} or "").strip()}`;
		if (item.operation === "format_date") return `{frappe.utils.format_date(${a}, "${item.fmt_config || ""}")}`;
		if (item.operation === "fmt_money") return `{frappe.utils.fmt_money(${a}, currency="${item.fmt_config || ""}")}`;
		return `{${a}}`;
	},
	compileToLabel: (item) => `${(item.operation || "text").toUpperCase()}(${item.field_a || "?"})`,
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 4. Math Strategy ───
registerStrategy("math", {
	label: __("Math"),
	description: __("Perform arithmetic (+, -, *, /) and math calculations (min, max, round)."),
	icon: "fa fa-calculator",
	component: MathResolver,
	defaultState: () => ({
		operation: "+",
		field_a: "",
		field_b_type: "field",
		field_b: "",
		constant_b: 0,
		precision: 2,
	}),
	compileToCode: (item) => {
		const a = item.field_a ? `frappe.utils.flt(${toDocExpression(item.field_a)})` : "0";
		const b = item.field_b_type === "field" ? (item.field_b ? `frappe.utils.flt(${toDocExpression(item.field_b)})` : "0") : String(item.constant_b ?? 0);
		const prec = item.precision ?? 2;
		if (item.operation === "min") return `{frappe.utils.flt(min(${a}, ${b}), ${prec})}`;
		if (item.operation === "max") return `{frappe.utils.flt(max(${a}, ${b}), ${prec})}`;
		if (item.operation === "round") return `{frappe.utils.flt(${a}, ${prec})}`;
		return `{frappe.utils.flt(${a} ${item.operation} ${b}, ${prec})}`;
	},
	compileToLabel: (item) => {
		const a = item.field_a || "?";
		const b = item.field_b_type === "field" ? item.field_b || "?" : item.constant_b;
		return `Math: ${a} ${item.operation} ${b}`;
	},
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 5. Collection Strategy ───
registerStrategy("collection", {
	label: __("Collection"),
	description: __("Filter, search, check, or extract values from child tables or list arrays."),
	icon: "fa fa-list-ol",
	component: CollectionResolver,
	defaultState: () => ({ source: "", operation: "any", target_field: "", condition: null }),
	compileToCode: (item) => `{${(item.operation || "any").toUpperCase()}(${item.source || "doc.items"})}`,
	compileToLabel: (item) => `${(item.operation || "any").toUpperCase()}(${item.source || "?"})`,
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 6. Aggregate Strategy ───
registerStrategy("aggregate", {
	label: __("Aggregate"),
	description: __("Calculate scalar numeric metrics (Sum, Average, Min, Max, Count) over child tables."),
	icon: "fa fa-table",
	component: AggregateResolver,
	defaultState: () => ({ agg_table: "", agg_field: "", agg_op: "sum" }),
	compileToCode: (item) => {
		const tbl = toDocExpression(item.agg_table || '""');
		const fld = item.agg_field || '""';
		if (item.agg_op === "count") return `{len(${tbl})}`;
		if (item.agg_op === "avg") return `{sum([frappe.utils.flt(r.get("${fld}")) for r in ${tbl}]) / (len(${tbl}) or 1)}`;
		return `{sum([frappe.utils.flt(r.get("${fld}")) for r in ${tbl}])}`;
	},
	compileToLabel: (item) => `${(item.agg_op || "sum").toUpperCase()}(${item.agg_table || "?"}.${item.agg_field || "?"})`,
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 7. Lookup Strategy ───
registerStrategy("lookup", {
	label: __("Lookup"),
	description: __("Fetch single field values or verify existence in linked database records."),
	icon: "fa fa-search",
	component: LookupResolver,
	defaultState: () => ({ operation: "get", link_field: "", linked_doctype: "", fetch_field: "" }),
	compileToCode: (item) => {
		const dt = item.linked_doctype ? `"${item.linked_doctype}"` : '""';
		const link = item.link_field ? toDocExpression(item.link_field) : '""';
		if (item.operation === "exists") return `{bool(frappe.db.exists(${dt}, ${link}))}`;
		return `{frappe.db.get_value(${dt}, ${link}, "${item.fetch_field || ""}")}`;
	},
	compileToLabel: (item) => `${item.linked_doctype || "?"}.${item.fetch_field || "?"} ← ${item.link_field || "?"}`,
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 8. Conditional Strategy ───
registerStrategy("conditional", {
	label: __("Conditional"),
	description: __("Evaluate if-then-else conditions returning custom values."),
	icon: "fa fa-code-fork",
	component: ConditionalResolver,
	defaultState: () => ({ condition: null, true_value: "", false_value: "" }),
	compileToCode: (item) => `IF-THEN-ELSE("${item.true_value}", "${item.false_value}")`,
	compileToLabel: (item) => `IF ? THEN "${item.true_value}" ELSE "${item.false_value}"`,
	validate: (item) => ({ isValid: true, errors: [] }),
});

// ─── 9. Type Conversion Strategy ───
registerStrategy("type_conversion", {
	label: __("Type Conversion"),
	description: __("Cast values explicitly to text, integer, decimal, boolean, date, or datetime."),
	icon: "fa fa-exchange",
	component: TypeConversionResolver,
	defaultState: () => ({ operation: "text", field: "" }),
	compileToCode: (item) => `CAST(${toDocExpression(item.field || '""')} AS ${(item.operation || "text").toUpperCase()})`,
	compileToLabel: (item) => `Cast ${item.field || "?"} to ${item.operation}`,
	validate: (item) => ({ isValid: true, errors: [] }),
});
