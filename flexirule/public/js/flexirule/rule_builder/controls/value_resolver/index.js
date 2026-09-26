import DateFormulaResolver from "./components/DateFormulaResolver.vue";
import MathFormulaResolver from "./components/MathFormulaResolver.vue";
import FetchResolver from "./components/FetchResolver.vue";
import DateDiffResolver from "./components/DateDiffResolver.vue";
import AggregationResolver from "./components/AggregationResolver.vue";
import TextTransformResolver from "./components/TextTransformResolver.vue";
import SystemContextResolver from "./components/SystemContextResolver.vue";
import CollectionResolver from "./components/CollectionResolver.vue";

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
				errors.push(frappe.utils.format(__("Base field '{0}' not found"), item.base_field));
			}
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Collection Query Strategy ───
registerStrategy("collection", {
	label: __("Collection Query"),
	description: __(
		"Filter, search, aggregate, check, or extract values from child table rows or list variables."
	),
	icon: "fa fa-list-ol",
	component: CollectionResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		let defaultSource = "";
		if (fieldname) {
			const cleanName = String(fieldname).replace(/^(doc|vars)\./, "");
			const store = useStore();
			const dt = store.rule_doc?.document_type || props.doctype;
			const fields = store.doc_meta?.[dt];
			const isTable = fields?.some(
				(f) => f.fieldname === cleanName && f.fieldtype === "Table"
			);
			if (isTable) {
				defaultSource = `doc.${cleanName}`;
			}
		}
		return {
			source: defaultSource,
			operation: "any",
			target_field: "",
			condition: null,
		};
	},
	compileToCode: (item) => {
		const src = item.source || "doc.items";
		const op = (item.operation || "any").toUpperCase();
		if (["SUM", "AVG", "PLUCK", "UNIQUE"].includes(op)) {
			return `{${op}(${src}, "${item.target_field || ""}")}`;
		}
		return `{${op}(${src})}`;
	},
	compileToLabel: (item) => {
		const op = (item.operation || "any").toUpperCase();
		const src = item.source || "?";
		if (["SUM", "AVG", "PLUCK", "UNIQUE"].includes(op)) {
			return `${op}(${src}.${item.target_field || "?"})`;
		}
		return `${op}(${src})`;
	},
	validate: (item) => {
		const errors = [];
		if (!item.source) {
			errors.push(__("Source collection is required"));
		}
		if (["sum", "avg", "pluck", "unique"].includes(item.operation) && !item.target_field) {
			errors.push(__("Target field is required for this operation"));
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
			errors.push(frappe.utils.format(__("Field A '{0}' not found"), item.field_a));
		}

		if (item.field_b_type === "field") {
			if (!item.field_b) {
				errors.push(__("Field B is required"));
			} else if (!validateField(item.field_b, dt, store)) {
				errors.push(frappe.utils.format(__("Field B '{0}' not found"), item.field_b));
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
				errors.push(
					frappe.utils.format(__("Start field '{0}' not found"), item.diff_start_field)
				);
			}
		}
		if (item.diff_end_type === "doc_field") {
			if (!item.diff_end_field) {
				errors.push(__("End field is required"));
			} else if (!validateField(item.diff_end_field, dt, store)) {
				errors.push(
					frappe.utils.format(__("End field '{0}' not found"), item.diff_end_field)
				);
			}
		}
		return { isValid: errors.length === 0, errors };
	},
});

// ─── Aggregation Strategy (Legacy) ───
registerStrategy("child_aggregation", {
	hidden: true,
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
			errors.push(frappe.utils.format(__("Table field '{0}' not found"), item.agg_table));
		}

		if (item.agg_op !== "count") {
			if (!item.agg_field) {
				errors.push(__("Numeric field is required"));
			} else {
				const fields = store.doc_meta[dt];
				const tableField = fields?.find((f) => f.fieldname === item.agg_table);
				if (tableField && tableField.options) {
					if (!validateField(item.agg_field, tableField.options, store)) {
						errors.push(
							frappe.utils.format(
								__("Field '{0}' not found in child table '{1}'"),
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

// ─── Text Transform Strategy ───
registerStrategy("text", {
	label: __("Text Transform"),
	description: __(
		"Combine text fields, change casing, apply normalization pipelines, or format text using templates."
	),
	icon: "fa fa-font",
	component: TextTransformResolver,
	defaultState: (props) => {
		const fieldname = props.context?.fieldname || props.context?.target;
		const cleanField = fieldname ? String(fieldname).replace(/^(doc|vars)\./, "") : "";
		return {
			operation: "combine",
			config: {
				str_a_type: "field",
				str_a: cleanField,
				str_b_type: "constant",
				str_b: "",
				field: cleanField,
				case_mode: "uppercase",
				norm_field: cleanField,
				norm_profile: "Custom",
				norm_pipeline: ["trim"],
				fmt_field: cleanField,
				fmt_config: "",
			},
		};
	},
	compileToCode: (item) => {
		const op = item.operation || "combine";
		const cfg = item.config || {};

		if (op === "combine") {
			const valA =
				cfg.str_a_type === "field"
					? toDocExpression(cfg.str_a || '""')
					: `"${cfg.str_a || ""}"`;
			const valB =
				cfg.str_b_type === "field"
					? toDocExpression(cfg.str_b || '""')
					: `"${cfg.str_b || ""}"`;
			return `{str(${valA} or "") + str(${valB} or "")}`;
		}

		if (op === "case") {
			const f = cfg.field ? toDocExpression(cfg.field) : '""';
			const mode = cfg.case_mode || "uppercase";
			if (mode === "uppercase") return `{str(${f} or "").upper()}`;
			if (mode === "lowercase") return `{str(${f} or "").lower()}`;
			if (mode === "titlecase") return `{str(${f} or "").title()}`;
			return `{flexirule.ruleflow.utils.normalization.execute_normalization_pipeline(${f}, pipeline=["${mode}"])["normalized_value"]}`;
		}

		if (op === "normalize") {
			const f = cfg.norm_field ? toDocExpression(cfg.norm_field) : '""';
			if (cfg.norm_profile && cfg.norm_profile !== "Custom") {
				return `{flexirule.ruleflow.utils.normalization.execute_normalization_pipeline(${f}, profile="${cfg.norm_profile}")["normalized_value"]}`;
			}
			const pipeline = JSON.stringify(cfg.norm_pipeline || []);
			return `{flexirule.ruleflow.utils.normalization.execute_normalization_pipeline(${f}, pipeline=${pipeline})["normalized_value"]}`;
		}

		if (op === "format") {
			const f = cfg.fmt_field ? toDocExpression(cfg.fmt_field) : '""';
			const tmpl = cfg.fmt_config || "";
			return `{("${tmpl}").format(${f})}`;
		}

		return '""';
	},
	compileToLabel: (item) => {
		const op = item.operation || "combine";
		const cfg = item.config || {};

		if (op === "combine") {
			const a = cfg.str_a_type === "field" ? cfg.str_a : `"${cfg.str_a || ""}"`;
			const b = cfg.str_b_type === "field" ? cfg.str_b : `"${cfg.str_b || ""}"`;
			return `Combine(${a || "?"}, ${b || "?"})`;
		}

		if (op === "case") {
			return `Case[${cfg.case_mode || "upper"}](${cfg.field || "?"})`;
		}

		if (op === "normalize") {
			const src = cfg.norm_field || "?";
			if (cfg.norm_profile && cfg.norm_profile !== "Custom") {
				return `Normalize: ${src} (${cfg.norm_profile})`;
			}
			return `Normalize: ${src} (${(cfg.norm_pipeline || []).length} steps)`;
		}

		if (op === "format") {
			return `Format(${cfg.fmt_field || "?"})`;
		}

		return `Text Transform`;
	},
	validate: (item, props) => {
		const errors = [];
		const store = useStore();
		const dt = store.rule_doc?.document_type || props.doctype;
		const op = item.operation || "combine";
		const cfg = item.config || {};

		if (op === "combine") {
			if (cfg.str_a_type === "field") {
				if (!cfg.str_a) errors.push(__("Value A field is required"));
				else if (!validateField(cfg.str_a, dt, store))
					errors.push(frappe.utils.format(__("Field '{0}' not found"), cfg.str_a));
			}
			if (cfg.str_b_type === "field") {
				if (!cfg.str_b) errors.push(__("Value B field is required"));
				else if (!validateField(cfg.str_b, dt, store))
					errors.push(frappe.utils.format(__("Field '{0}' not found"), cfg.str_b));
			}
		} else if (op === "case") {
			if (!cfg.field) errors.push(__("Target field is required"));
			else if (!validateField(cfg.field, dt, store))
				errors.push(frappe.utils.format(__("Field '{0}' not found"), cfg.field));
		} else if (op === "normalize") {
			if (!cfg.norm_field) errors.push(__("Field is required"));
			else if (!validateField(cfg.norm_field, dt, store))
				errors.push(frappe.utils.format(__("Field '{0}' not found"), cfg.norm_field));
		} else if (op === "format") {
			if (!cfg.fmt_field) errors.push(__("Field is required"));
			else if (!validateField(cfg.fmt_field, dt, store))
				errors.push(frappe.utils.format(__("Field '{0}' not found"), cfg.fmt_field));
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
				errors.push(frappe.utils.format(__("Link field '{0}' not found"), item.link_field));
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
					frappe.utils.format(
						__("Field '{0}' not found in Source DocType '{1}'"),
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
