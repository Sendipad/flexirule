/**
 * Builder Utilities for FlexiRule
 * Centralizes the logic for compiling builder configurations into Python expressions and human-readable labels.
 */

const __ =
	window.__ ||
	((s) => {
		return s;
	});

/**
 * Resolves a field reference to a Python-safe expression, ensuring proper scoping.
 * @param {string} field - The field name or path
 * @returns {string} - Scoped field reference (e.g., 'doc.status', 'vars.my_var')
 */
function toDocExpression(field) {
	if (!field) return '""';
	const knownScopes = ["doc.", "vars.", "ctx.", "loop.", "row.", "item.", "caller.", "rule."];
	if (knownScopes.some((s) => String(field).startsWith(s))) {
		return field;
	}
	return `doc.${field}`;
}

/**
 * Compiles a builder configuration object into a Python expression.
 *
 * @param {Object} item - The builder configuration item
 * @param {string} fallbackField - Default field to use if none is specified
 * @returns {string} - Python expression wrapped in braces {}
 */
export function compileToCode(item, fallbackField = "") {
	if (!item || !item.kind) return "";

	if (item.kind === "math_formula") {
		const a = item.field_a ? `frappe.utils.flt(${toDocExpression(item.field_a)})` : "0";
		const b =
			item.field_b_type === "field"
				? item.field_b
					? `frappe.utils.flt(${toDocExpression(item.field_b)})`
					: "0"
				: String(item.constant_b ?? 0);
		const prec = item.precision ?? 2;
		return `{frappe.utils.flt(${a} ${item.math_op} ${b}, ${prec})}`;
	}

	if (item.kind === "date_diff") {
		const start =
			item.diff_start_type === "today"
				? "frappe.utils.nowdate()"
				: toDocExpression(item.diff_start_field);
		const end =
			item.diff_end_type === "today"
				? "frappe.utils.nowdate()"
				: toDocExpression(item.diff_end_field || fallbackField);

		if (item.diff_unit === "days") return `{frappe.utils.date_diff(${end}, ${start})}`;
		if (item.diff_unit === "months") return `{frappe.utils.month_diff(${end}, ${start})}`;
		return `{int(frappe.utils.month_diff(${end}, ${start}) / 12)}`;
	}

	if (item.kind === "child_aggregation") {
		const tbl = item.agg_table || '""';
		const fld = item.agg_field || '""';
		const tblExpr = toDocExpression(tbl);
		if (item.agg_op === "count") return `{len(${tblExpr})}`;
		if (item.agg_op === "avg") {
			return `{sum([frappe.utils.flt(row.get("${fld}")) for row in ${tblExpr}]) / (len(${tblExpr}) or 1)}`;
		}
		return `{sum([frappe.utils.flt(row.get("${fld}")) for row in ${tblExpr}])}`;
	}

	if (item.kind === "string_formula") {
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
	}

	if (item.kind === "normalization") {
		const f = item.norm_field ? toDocExpression(item.norm_field) : '""';
		if (item.norm_op === "trim") return `{str(${f} or "").strip()}`;
		if (item.norm_op === "slug") return `{frappe.scrub(str(${f} or ""))}`;
		if (item.norm_op === "title") return `{str(${f} or "").title()}`;
		if (item.norm_op === "upper") return `{str(${f} or "").upper()}`;
		if (item.norm_op === "lower") return `{str(${f} or "").lower()}`;
		if (item.norm_op === "snake") return `{frappe.scrub(str(${f} or ""))}`;
	}

	if (item.kind === "format") {
		const f = item.fmt_field ? toDocExpression(item.fmt_field) : '""';
		const cfg = item.fmt_config || "";
		if (item.fmt_op === "format_date") return `{frappe.utils.format_date(${f}, "${cfg}")}`;
		if (item.fmt_op === "fmt_money") {
			const curr = cfg.includes(".") || cfg.includes("doc") ? cfg : `"${cfg}"`;
			return `{frappe.utils.fmt_money(${f}, currency=${curr})}`;
		}
		if (item.fmt_op === "format") return `{("${cfg}").format(${f})}`;
	}

	if (item.kind === "system_context") {
		if (item.sys_token === "role_check") {
			return `{"${item.sys_role}" in frappe.get_roles(frappe.session.user)}`;
		}
		return `{frappe.session.user}`;
	}

	// Default: date_formula
	const baseExpr =
		item.base_type === "today"
			? "frappe.utils.nowdate()"
			: toDocExpression(item.base_field || fallbackField);
	const offset = parseInt(item.offset_value || 0, 10);

	if (offset === 0 || !item.offset_unit) {
		return `{${baseExpr}}`;
	}

	if (item.offset_unit === "days") {
		return `{frappe.utils.add_days(${baseExpr}, ${offset})}`;
	}

	return `{frappe.utils.add_to_date(${baseExpr}, ${item.offset_unit}=${offset})}`;
}

/**
 * Compiles a builder configuration object into a human-readable label.
 *
 * @param {Object} item - The builder configuration item
 * @returns {string} - Human-readable text
 */
export function compileToLabel(item) {
	if (!item || !item.kind) return __("Configure");

	if (item.kind === "date_formula") {
		const base = item.base_type === "today" ? __("Today") : item.base_field || __("Doc Field");
		const offset = parseInt(item.offset_value || 0, 10);
		if (offset === 0) return base;
		const sign = offset > 0 ? "+" : "";
		return `${base} ${sign}${offset} ${item.offset_unit}`;
	}

	if (item.kind === "math_formula") {
		const a = item.field_a || "?";
		const b = item.field_b_type === "field" ? item.field_b || "?" : item.constant_b;
		return `${a} ${item.math_op} ${b}`;
	}

	if (item.kind === "date_diff") {
		const start = item.diff_start_type === "today" ? __("Today") : item.diff_start_field || "?";
		const end = item.diff_end_type === "today" ? __("Today") : item.diff_end_field || "?";
		return `${end} − ${start} (${item.diff_unit})`;
	}

	if (item.kind === "child_aggregation") {
		return `${(item.agg_op || "").toUpperCase()}(${item.agg_table || "?"}.${
			item.agg_field || "?"
		})`;
	}

	if (item.kind === "string_formula") {
		const ops = {
			concat: __("Concatenate"),
			fmt_money: __("Format Money"),
			uppercase: __("Uppercase"),
			lowercase: __("Lowercase"),
		};
		return ops[item.str_op] || __("String manipulation");
	}

	if (item.kind === "normalization") {
		return `${__(item.norm_op)}(${item.norm_field || "?"})`;
	}

	if (item.kind === "format") {
		return `${__(item.fmt_op)}(${item.fmt_field || "?"})`;
	}

	if (item.kind === "system_context") {
		if (item.sys_token === "user") return __("Current User");
		if (item.sys_token === "role_check") return __("Has Role");
	}

	return __("Configure");
}
