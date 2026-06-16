import DateFormulaResolver from "./components/DateFormulaResolver.vue";
import MathFormulaResolver from "./components/MathFormulaResolver.vue";
import FetchResolver from "./components/FetchResolver.vue";
import DateDiffResolver from "./components/DateDiffResolver.vue";
import AggregationResolver from "./components/AggregationResolver.vue";
import StringFormulaResolver from "./components/StringFormulaResolver.vue";
import NormalizationResolver from "./components/NormalizationResolver.vue";
import FormatResolver from "./components/FormatResolver.vue";
import SystemContextResolver from "./components/SystemContextResolver.vue";

import { registerStrategy } from "./strategies";
import { __, toDocExpression, validateField } from "./utils";
import { useStore } from "../../stores";

// ─── Date Formula Strategy ───
registerStrategy("date_formula", {
	label: __("Date Formula"),
	description: __(
		"Calculate a date by adding or subtracting days, months, or years from a base field or today."
	),
	icon: "fa fa-calendar",
	component: DateFormulaResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		let baseField = "";
		let baseType = "today";
		if (fieldname) {
			baseType = "doc_field";
			baseField = String(fieldname).replace(/^(doc|vars)\./, "");
		}
		return {
			base_type: baseType,
			base_field: baseField,
			offset_sign: "+",
			offset_value: 0,
			offset_unit: "days",
		};
	},
	compileToCode: (item) => {
		const baseExpr =
			item.base_type === "today"
				? "frappe.utils.nowdate()"
				: toDocExpression(item.base_field);
		let offset = parseInt(item.offset_value || 0, 10);
		if (item.offset_sign === "-" && offset > 0) offset = -offset;

		if (offset === 0 || !item.offset_unit) return `{${baseExpr}}`;

		if (item.offset_unit === "days") {
			return `{frappe.utils.add_days(${baseExpr}, ${offset})}`;
		}
		return `{frappe.utils.add_to_date(${baseExpr}, ${item.offset_unit}=${offset})}`;
	},
	compileToLabel: (item) => {
		const base = item.base_type === "today" ? __("Today") : item.base_field || __("Field");
		let offset = parseInt(item.offset_value || 0, 10);
		if (item.offset_sign === "-" && offset > 0) offset = -offset;
		if (offset === 0) return `Date: ${base}`;
		const sign = offset > 0 ? "+" : "";
		return `Date: ${base} ${sign}${offset} ${item.offset_unit}`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (item.base_type === "doc_field") {
			if (!item.base_field) {
				errors.push(__("Base field is required"));
			} else if (!validateField(item.base_field, dt, store)) {
				errors.push(__("Base field '{0}' not found").format(item.base_field));
			}
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Math Formula Strategy ───
registerStrategy("math_formula", {
	label: __("Math Formula"),
	description: __("Perform basic arithmetic between two fields or a field and a constant value."),
	icon: "fa fa-calculator",
	component: MathFormulaResolver,
	defaultState: () => ({
		field_a: "",
		math_op: "+",
		field_b_type: "field",
		field_b: "",
		constant_b: 0,
		precision: 2,
	}),
	compileToCode: (item) => {
		const a = item.field_a ? `frappe.utils.flt(${toDocExpression(item.field_a)})` : "0";
		const b =
			item.field_b_type === "field"
				? item.field_b
					? `frappe.utils.flt(${toDocExpression(item.field_b)})`
					: "0"
				: String(item.constant_b ?? 0);
		const prec = item.precision ?? 2;
		return `{frappe.utils.flt(${a} ${item.math_op} ${b}, ${prec})}`;
	},
	compileToLabel: (item) => {
		const a = item.field_a || "?";
		const b = item.field_b_type === "field" ? item.field_b || "?" : item.constant_b;
		return `Calc: ${a} ${item.math_op} ${b}`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (!item.field_a) {
			errors.push(__("Field A is required"));
		} else if (!validateField(item.field_a, dt, store)) {
			errors.push(__("Field A '{0}' not found").format(item.field_a));
		}

		if (item.field_b_type === "field") {
			if (!item.field_b) {
				errors.push(__("Field B is required"));
			} else if (!validateField(item.field_b, dt, store)) {
				errors.push(__("Field B '{0}' not found").format(item.field_b));
			}
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Date Diff Strategy ───
registerStrategy("date_diff", {
	label: __("Date Difference"),
	description: __("Calculate the time difference between two dates in days, months, or years."),
	icon: "fa fa-calendar-minus-o",
	component: DateDiffResolver,
	defaultState: () => ({
		diff_start_type: "today",
		diff_start_field: "",
		diff_end_type: "doc_field",
		diff_end_field: "",
		diff_unit: "days",
	}),
	compileToCode: (item) => {
		const start =
			item.diff_start_type === "today"
				? "frappe.utils.nowdate()"
				: toDocExpression(item.diff_start_field);
		const end =
			item.diff_end_type === "today"
				? "frappe.utils.nowdate()"
				: toDocExpression(item.diff_end_field);

		if (item.diff_unit === "days") return `{frappe.utils.date_diff(${end}, ${start})}`;
		if (item.diff_unit === "months") return `{frappe.utils.month_diff(${end}, ${start})}`;
		return `{int(frappe.utils.month_diff(${end}, ${start}) / 12)}`;
	},
	compileToLabel: (item) => {
		const start = item.diff_start_type === "today" ? __("Today") : item.diff_start_field || "?";
		const end = item.diff_end_type === "today" ? __("Today") : item.diff_end_field || "?";
		return `${end} − ${start} (${item.diff_unit})`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (item.diff_start_type === "doc_field") {
			if (!item.diff_start_field) {
				errors.push(__("Start field is required"));
			} else if (!validateField(item.diff_start_field, dt, store)) {
				errors.push(__("Start field '{0}' not found").format(item.diff_start_field));
			}
		}
		if (item.diff_end_type === "doc_field") {
			if (!item.diff_end_field) {
				errors.push(__("End field is required"));
			} else if (!validateField(item.diff_end_field, dt, store)) {
				errors.push(__("End field '{0}' not found").format(item.diff_end_field));
			}
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Aggregation Strategy ───
registerStrategy("child_aggregation", {
	label: __("Child Table Aggregation"),
	description: __("Aggregate numeric values from a child table using Sum, Average, or Count."),
	icon: "fa fa-table",
	component: AggregationResolver,
	defaultState: () => ({
		agg_table: "",
		agg_field: "",
		agg_op: "sum",
	}),
	compileToCode: (item) => {
		const tbl = item.agg_table || '""';
		const fld = item.agg_field || '""';
		const tblExpr = toDocExpression(tbl);
		if (item.agg_op === "count") return `{len(${tblExpr})}`;
		if (item.agg_op === "avg") {
			return `{sum([frappe.utils.flt(row.get("${fld}")) for row in ${tblExpr}]) / (len(${tblExpr}) or 1)}`;
		}
		return `{sum([frappe.utils.flt(row.get("${fld}")) for row in ${tblExpr}])}`;
	},
	compileToLabel: (item) => {
		return `${(item.agg_op || "").toUpperCase()}(${item.agg_table || "?"}.${
			item.agg_field || "?"
		})`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (!item.agg_table) {
			errors.push(__("Child table is required"));
		} else if (!validateField(item.agg_table, dt, store)) {
			errors.push(__("Table field '{0}' not found").format(item.agg_table));
		}

		if (item.agg_op !== "count") {
			if (!item.agg_field) {
				errors.push(__("Numeric field is required"));
			} else {
				// For child tables, we'd need to validate against the child doctype's meta
				const fields = store.doc_meta[dt];
				const tableField = fields?.find((f) => f.fieldname === item.agg_table);
				if (tableField && tableField.options) {
					if (!validateField(item.agg_field, tableField.options, store)) {
						errors.push(
							__("Field '{0}' not found in child table '{1}'").format(
								item.agg_field,
								tableField.options
							)
						);
					}
				}
			}
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── String Formula Strategy ───
registerStrategy("string_formula", {
	label: __("String Manipulation"),
	description: __("Combine text fields, change casing, or format currency strings."),
	icon: "fa fa-font",
	component: StringFormulaResolver,
	defaultState: () => ({
		str_op: "concat",
		str_a_type: "field",
		str_a: "",
		str_b_type: "constant",
		str_b: "",
	}),
	compileToCode: (item) => {
		const valA =
			item.str_a_type === "field"
				? toDocExpression(item.str_a || '""')
				: `"${item.str_a || ""}"`;
		const valB =
			item.str_b_type === "field"
				? toDocExpression(item.str_b || '""')
				: `"${item.str_b || ""}"`;

		if (item.str_op === "concat") return `{str(${valA} or "") + str(${valB} or "")}`;
		if (item.str_op === "uppercase") return `{str(${valA} or "").upper()}`;
		if (item.str_op === "lowercase") return `{str(${valA} or "").lower()}`;
		if (item.str_op === "fmt_money")
			return `{frappe.utils.fmt_money(${valA}, currency=${valB})}`;
		return `{${valA}}`;
	},
	compileToLabel: (item) => {
		const ops = {
			concat: __("Concat"),
			fmt_money: __("Fmt Money"),
			uppercase: __("Upper"),
			lowercase: __("Lower"),
		};
		const op = ops[item.str_op] || __("String");
		const valA = item.str_a_type === "field" ? item.str_a : `"${item.str_a || ""}"`;
		const valB = item.str_b_type === "field" ? item.str_b : `"${item.str_b || ""}"`;

		if (["concat", "fmt_money"].includes(item.str_op)) {
			return `${op}(${valA || "?"}, ${valB || "?"})`;
		}
		return `${op}(${valA || "?"})`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (item.str_a_type === "field") {
			if (!item.str_a) {
				errors.push(__("Value A field is required"));
			} else if (!validateField(item.str_a, dt, store)) {
				errors.push(__("Field '{0}' not found").format(item.str_a));
			}
		}

		if (item.str_b_type === "field" && ["concat", "fmt_money"].includes(item.str_op)) {
			if (!item.str_b) {
				errors.push(__("Value B field is required"));
			} else if (!validateField(item.str_b, dt, store)) {
				errors.push(__("Field '{0}' not found").format(item.str_b));
			}
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Normalization Strategy ───
registerStrategy("normalization", {
	label: __("Normalization"),
	description: __(
		"Clean up text data by trimming whitespace, changing case, or converting to slug/snake case."
	),
	icon: "fa fa-refresh",
	component: NormalizationResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		return {
			norm_op: "trim",
			norm_field: fieldname ? String(fieldname).replace(/^(doc|vars)\./, "") : "",
		};
	},
	compileToCode: (item) => {
		const f = item.norm_field ? toDocExpression(item.norm_field) : '""';
		if (item.norm_op === "trim") return `{str(${f} or "").strip()}`;
		if (item.norm_op === "slug") return `{frappe.scrub(str(${f} or ""))}`;
		if (item.norm_op === "title") return `{str(${f} or "").title()}`;
		if (item.norm_op === "upper") return `{str(${f} or "").upper()}`;
		if (item.norm_op === "lower") return `{str(${f} or "").lower()}`;
		if (item.norm_op === "snake") return `{frappe.scrub(str(${f} or ""))}`;
	},
	compileToLabel: (item) => {
		const ops = {
			trim: __("Trim"),
			slug: __("Slug"),
			title: __("Title"),
			upper: __("Upper"),
			lower: __("Lower"),
			snake: __("Snake"),
		};
		return `${ops[item.norm_op] || __("Norm")}(${item.norm_field || "?"})`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (!item.norm_field) {
			errors.push(__("Field is required"));
		} else if (!validateField(item.norm_field, dt, store)) {
			errors.push(__("Field '{0}' not found").format(item.norm_field));
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Format Strategy ───
registerStrategy("format", {
	label: __("Format"),
	icon: "fa fa-paint-brush",
	component: FormatResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		return {
			fmt_op: "format_date",
			fmt_field: fieldname ? String(fieldname).replace(/^(doc|vars)\./, "") : "",
			fmt_config: "",
		};
	},
	compileToCode: (item) => {
		const f = item.fmt_field ? toDocExpression(item.fmt_field) : '""';
		const cfg = item.fmt_config || "";
		if (item.fmt_op === "format_date") return `{frappe.utils.format_date(${f}, "${cfg}")}`;
		if (item.fmt_op === "fmt_money") {
			const curr = cfg.includes(".") || cfg.includes("doc") ? cfg : `"${cfg}"`;
			return `{frappe.utils.fmt_money(${f}, currency=${curr})}`;
		}
		if (item.fmt_op === "format") return `{("${cfg}").format(${f})}`;
	},
	compileToLabel: (item) => `${__(item.fmt_op)}(${item.fmt_field || "?"})`,
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (!item.fmt_field) {
			errors.push(__("Field is required"));
		} else if (!validateField(item.fmt_field, dt, store)) {
			errors.push(__("Field '{0}' not found").format(item.fmt_field));
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Fetch Strategy ───
registerStrategy("fetch", {
	label: __("Fetch From Link"),
	icon: "fa fa-link",
	component: FetchResolver,
	defaultState: () => ({
		link_source_type: "doc_field",
		link_field: "",
		fetch_field: "",
		linked_doctype: "",
	}),
	compileToCode: (item) => {
		const dt = item.linked_doctype || "";
		const knownScopes = ["doc.", "vars.", "ctx.", "loop.", "row.", "item.", "caller.", "rule."];
		const dtExpr = knownScopes.some((s) => String(dt).startsWith(s)) ? dt : `"${dt}"`;
		const link = item.link_field ? toDocExpression(item.link_field) : "";
		const field = item.fetch_field || "";
		return `{frappe.db.get_value(${dtExpr}, ${link}, "${field}")}`;
	},
	compileToLabel: (item) => {
		const dt = item.linked_doctype || __("Linked Doc");
		const field = item.fetch_field || "?";
		const link = item.link_field || "?";
		return `${dt}.${field}\n← ${link}`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;

		if (!item.linked_doctype) {
			errors.push(__("Source DocType is required"));
		}

		if (item.link_source_type === "doc_field") {
			if (!item.link_field) {
				errors.push(__("Link field is required"));
			} else if (!validateField(item.link_field, dt, store)) {
				errors.push(__("Link field '{0}' not found").format(item.link_field));
			}
		}

		if (!item.fetch_field) {
			errors.push(__("Fetch field is required"));
		} else if (
			item.linked_doctype &&
			!item.linked_doctype.startsWith("doc.") &&
			!item.linked_doctype.startsWith("vars.")
		) {
			if (!validateField(item.fetch_field, item.linked_doctype, store)) {
				errors.push(
					__("Field '{0}' not found in Source DocType '{1}'").format(
						item.fetch_field,
						item.linked_doctype
					)
				);
			}
		}

		return { isValid: errors.length === 0, errors };
	},
});

// ─── System Context Strategy ───
registerStrategy("system_context", {
	label: __("System Context"),
	icon: "fa fa-globe",
	component: SystemContextResolver,
	defaultState: () => ({
		sys_token: "user",
		sys_role: "",
	}),
	compileToCode: (item) => {
		if (item.sys_token === "role_check") {
			return `{"${item.sys_role}" in frappe.get_roles(frappe.session.user)}`;
		}
		return `{frappe.session.user}`;
	},
	compileToLabel: (item) => {
		if (item.sys_token === "user") return __("Current User");
		if (item.sys_token === "role_check") return __("Has Role");
		return __("System Context");
	},
	validate: (item) => {
		const errors = [];
		if (item.sys_token === "role_check" && !item.sys_role)
			errors.push(__("Role name is required"));
		return { isValid: errors.length === 0, errors };
	},
});
