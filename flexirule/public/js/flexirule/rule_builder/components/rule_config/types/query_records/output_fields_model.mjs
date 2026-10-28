import { normalizeResolvedOutputField } from "../../../../../utils/output_schema.mjs";

export const RESULT_SHAPES = Object.freeze({
	documentNames: "document_names",
	wholeDocuments: "whole_documents",
	selectedFields: "selected_fields",
	embeddedChildren: "embedded_children",
});
export const AGGREGATE_FUNCTIONS = Object.freeze(["count", "sum", "avg", "min", "max"]);

const AGGREGATE_SET = new Set(AGGREGATE_FUNCTIONS);
const ALIAS_PATTERN = /^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/;
export function humanizeAlias(value) {
	return String(value ?? "")
		.split("_")
		.filter(Boolean)
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ");
}
function clone(value) {
	if (value === undefined) return undefined;
	return JSON.parse(JSON.stringify(value));
}
function isObject(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}
export function isCustomResultShape(shape) {
	return shape === RESULT_SHAPES.selectedFields || shape === RESULT_SHAPES.embeddedChildren;
}
export function isChildFieldSelection(value) {
	if (!isObject(value)) return false;
	return Object.entries(value).some(([key, nested]) => key !== "as" && Array.isArray(nested));
}
function isAggregateDescriptor(value) {
	if (!isObject(value)) return false;
	return Object.keys(value).some((key) => AGGREGATE_SET.has(key.toLowerCase()));
}
export function inferResultShape(fields, explicitShape) {
	if (Object.values(RESULT_SHAPES).includes(explicitShape)) return explicitShape;
	if (fields === "*" || (Array.isArray(fields) && fields.length === 1 && fields[0] === "*")) {
		return RESULT_SHAPES.wholeDocuments;
	}
	if (fields == null || fields === "" || (Array.isArray(fields) && fields.length === 0)) {
		return RESULT_SHAPES.documentNames;
	}
	if (Array.isArray(fields) && fields.length === 1 && fields[0] === "name") {
		return RESULT_SHAPES.documentNames;
	}
	const list = Array.isArray(fields) ? fields : [fields];
	if (list.some((item) => isChildFieldSelection(item) && !isAggregateDescriptor(item))) {
		return RESULT_SHAPES.embeddedChildren;
	}
	return RESULT_SHAPES.selectedFields;
}
function splitTopLevelExpressions(input) {
	const parts = [];
	let start = 0;
	let depth = 0;
	let quote = null;
	let escaped = false;
	for (let index = 0; index < input.length; index += 1) {
		const char = input[index];
		if (quote) {
			if (escaped) escaped = false;
			else if (char === "\\") escaped = true;
			else if (char === quote) quote = null;
			continue;
		}
		if (char === "'" || char === '"' || char === "`") quote = char;
		else if (char === "(" || char === "[" || char === "{") depth += 1;
		else if (char === ")" || char === "]" || char === "}") depth = Math.max(0, depth - 1);
		else if (char === "," && depth === 0) {
			const part = input.slice(start, index).trim();
			if (part) parts.push(part);
			start = index + 1;
		}
	}
	const finalPart = input.slice(start).trim();
	if (finalPart) parts.push(finalPart);
	return parts;
}
function parseAlias(expression) {
	const match = String(expression)
		.trim()
		.match(/^(.+?)\s+as\s+(.+)$/i);
	if (!match) return { expression: String(expression).trim(), alias: "" };
	return { expression: match[1].trim(), alias: match[2] };
}
function createRow(kind, index, values = {}) {
	return {
		id: "output-" + index,
		kind,
		field: "",
		alias: "",
		functionName: "count",
		tableField: "",
		fields: [],
		expression: "",
		originalValue: undefined,
		dirty: false,
		...values,
	};
}
function parseTextField(value, index) {
	const raw = String(value ?? "").trim();
	const withAlias = parseAlias(raw);
	const functionMatch = withAlias.expression.match(
		/^(count|sum|avg|min|max)\s*\(\s*([^)]+?)\s*\)$/i
	);
	if (functionMatch) {
		return createRow("function", index, {
			functionName: functionMatch[1].toLowerCase(),
			field: functionMatch[2].trim(),
			alias: withAlias.alias,
		});
	}
	if (
		raw === "" ||
		/^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$/.test(withAlias.expression)
	) {
		return createRow("field", index, { field: withAlias.expression, alias: withAlias.alias });
	}
	return createRow("raw", index, { expression: raw, originalValue: raw });
}
/**
 * Convert persisted Frappe field grammar into editable rows.
 * Aggregate descriptors are accepted on input so the UI can recognize them,
 * but normalized to native Frappe v15 string expressions on save. Branch capability
 * tests show get_query rejects aggregate dictionaries.
 */
export function parseOutputFields(value) {
	let list;
	if (Array.isArray(value)) {
		list = value;
	} else if (typeof value === "string" && value.trim()) {
		const raw = value.trim();
		list = raw === "*" ? [raw] : splitTopLevelExpressions(raw);
	} else {
		list = [];
	}
	const rows = [];
	let index = 0;
	for (const item of list) {
		if (typeof item === "string" || typeof item === "number") {
			rows.push(parseTextField(item, index++));
			continue;
		}
		if (isObject(item)) {
			if (item.kind === "literal") {
				rows.push(
					createRow("literal", index++, {
						fieldname: String(item.fieldname ?? "").trim(),
						label: String(item.label ?? "").trim(),
						fieldtype: String(item.fieldtype || "Data"),
						options: item.options,
						reqd: item.reqd,
						value_spec: isObject(item.value_spec)
							? clone(item.value_spec)
							: { mode: "static", value: item.value ?? "" },
						originalValue: clone(item),
					})
				);
				continue;
			}
			const aggregateKey = Object.keys(item).find((key) =>
				AGGREGATE_SET.has(key.toLowerCase())
			);
			if (aggregateKey) {
				rows.push(
					createRow("function", index++, {
						functionName: aggregateKey.toLowerCase(),
						field: String(item[aggregateKey] ?? ""),
						alias: String(item.as ?? ""),
						originalValue: clone(item),
					})
				);
				continue;
			}
			const childEntries = Object.entries(item).filter(
				([key, nested]) => key !== "as" && Array.isArray(nested)
			);
			if (childEntries.length) {
				for (const [tableField, childFields] of childEntries) {
					rows.push(
						createRow("child", index++, { tableField, fields: clone(childFields) })
					);
				}
				continue;
			}
		}
		rows.push(
			createRow("raw", index++, {
				expression: JSON.stringify(item),
				originalValue: clone(item),
			})
		);
	}
	return rows;
}
export function serializeOutputFields(rows) {
	return (Array.isArray(rows) ? rows : []).map((row) => {
		if (row.kind === "field") {
			const field = String(row.field ?? "").trim();
			const alias = String(row.alias ?? "").trim();
			return field && alias ? field + " as " + alias : field;
		}
		if (row.kind === "function") {
			const fn = String(row.functionName ?? "count").toLowerCase();
			const field = String(row.field ?? "").trim();
			const alias = String(row.alias ?? "").trim();
			const expression = fn + "(" + field + ")";
			return alias ? expression + " as " + alias : expression;
		}
		if (row.kind === "child") {
			const tableField = String(row.tableField ?? "").trim();
			const fields = Array.isArray(row.fields) ? clone(row.fields) : [];
			return tableField ? { [tableField]: fields } : {};
		}
		if (row.kind === "literal") {
			const fieldname = String(row.fieldname ?? "").trim();
			return {
				kind: "literal",
				fieldname,
				label: String(row.label ?? "").trim() || humanizeAlias(fieldname),
				fieldtype: String(row.fieldtype || "Data"),
				...(row.options ? { options: String(row.options) } : {}),
				reqd: Number(row.reqd) === 1 ? 1 : 0,
				value_spec: isObject(row.value_spec)
					? clone(row.value_spec)
					: { mode: "static", value: "" },
			};
		}
		if (row.dirty) {
			const expression = String(row.expression ?? "").trim();
			try {
				return JSON.parse(expression);
			} catch {
				return expression;
			}
		}
		return clone(row.originalValue !== undefined ? row.originalValue : row.expression);
	});
}
/**
 * Build the output schema from Fetch Records' configured result shape and field
 * grammar. The caller supplies metadata keyed by field path, so aliases and
 * aggregate expressions are mapped to their actual result keys before schema
 * propagation to downstream actions.
 */
export function buildResolvedOutputSchema({
	shape,
	fields,
	fieldInfoByPath = {},
	wholeDocumentFields = [],
	systemFields = [],
}) {
	const lookup = (path) => {
		if (fieldInfoByPath instanceof Map) return fieldInfoByPath.get(path);
		return fieldInfoByPath?.[path];
	};
	const schema = [];
	const seen = new Set();
	const sourceFallback = (field, kind) => ({
		kind,
		...(field?.fieldname ? { fieldname: field.fieldname, expression: field.fieldname } : {}),
	});
	const add = (field, fallbackSourceKind = "unknown") => {
		if (!field?.fieldname || seen.has(field.fieldname)) return;
		seen.add(field.fieldname);
		const source =
			field.source && typeof field.source === "object" && !Array.isArray(field.source)
				? clone(field.source)
				: sourceFallback(field, fallbackSourceKind);
		schema.push(
			normalizeResolvedOutputField(
				{
					label: field.label || field.fieldname,
					fieldname: field.fieldname,
					fieldtype: field.fieldtype || "Data",
					...(field.options ? { options: field.options } : {}),
					reqd: field.reqd ?? field.mandatory ?? 0,
					source,
				},
				{ fallbackSourceKind }
			)
		);
	};
	const sourceInfo = (path) =>
		lookup(String(path ?? "").trim()) || {
			fieldname: path,
			label: path,
			fieldtype: "Data",
		};
	const aliasLabel = (alias) => humanizeAlias(alias);

	if (shape === RESULT_SHAPES.documentNames) {
		add(
			lookup("name") || {
				fieldname: "name",
				label: "ID (name)",
				fieldtype: "Data",
			},
			"system"
		);
		return schema;
	}
	if (shape === RESULT_SHAPES.wholeDocuments) {
		for (const field of wholeDocumentFields || []) add(field, "field");
		for (const field of systemFields || []) add(field, "system");
		return schema;
	}

	for (const row of parseOutputFields(fields)) {
		if (row.kind === "field") {
			const source = String(row.field ?? "").trim();
			if (!source) continue;
			const info = sourceInfo(source);
			const alias = String(row.alias ?? "").trim();
			add({
				...info,
				fieldname: alias || source,
				label: alias ? aliasLabel(alias) : info.label || source,
				source: {
					kind: source.includes(".") ? "child_field" : "field",
					fieldname: source,
					expression: alias ? source + " as " + alias : source,
				},
			});
		} else if (row.kind === "function") {
			const source = String(row.field ?? "").trim();
			const fn = String(row.functionName ?? "count").toLowerCase();
			const alias = String(row.alias ?? "").trim();
			if (!source || !alias) continue;
			const info = sourceInfo(source);
			const numericType = [
				"Currency",
				"Float",
				"Int",
				"Percent",
				"Rating",
				"Duration",
			].includes(info.fieldtype);
			add({
				fieldname: alias,
				label: aliasLabel(alias),
				fieldtype:
					fn === "count"
						? "Int"
						: fn === "avg"
						? "Float"
						: ["min", "max"].includes(fn)
						? info.fieldtype || "Data"
						: numericType
						? info.fieldtype
						: "Float",
				reqd: 0,
				source: {
					kind: "aggregate",
					function: fn,
					fieldname: source,
					expression: fn + "(" + source + ") as " + alias,
				},
			});
		} else if (row.kind === "child") {
			const tableField = String(row.tableField ?? "").trim();
			if (!tableField) continue;
			const tableInfo = sourceInfo(tableField);
			add({
				fieldname: tableField,
				label: tableInfo.label || tableField,
				fieldtype: "Table",
				options: tableInfo.options,
				reqd: 0,
				source: { kind: "child_table", fieldname: tableField, expression: tableField },
			});
			for (const childField of Array.isArray(row.fields) ? row.fields : []) {
				const path = tableField + "." + childField;
				const info = sourceInfo(path);
				add({
					...info,
					fieldname: path,
					label: (tableInfo.label || tableField) + ": " + (info.label || childField),
					source: {
						kind: "child_field",
						table_fieldname: tableField,
						fieldname: childField,
						expression: path,
					},
				});
			}
		} else if (row.kind === "literal") {
			const fieldname = String(row.fieldname ?? "").trim();
			if (!fieldname) continue;
			const valueSpec = isObject(row.value_spec)
				? clone(row.value_spec)
				: { mode: "static", value: "" };
			const valueMode = String(valueSpec.mode || "static").toLowerCase();
			add({
				fieldname,
				label: String(row.label || "").trim() || aliasLabel(fieldname),
				fieldtype: String(row.fieldtype || "Data"),
				...(row.options ? { options: row.options } : {}),
				reqd: 0,
				source: {
					kind: valueMode === "static" ? "literal" : "dynamic",
					fieldname,
					value_spec: valueSpec,
				},
			});
		} else if (row.kind === "raw") {
			const expression = String(row.expression ?? "").trim();
			if (!expression) continue;
			const match = expression.match(/^(.+?)\s+as\s+(.+)$/i);
			const alias = match ? match[2].trim() : "";
			const fieldname = alias || expression;
			add({
				fieldname,
				label: alias ? aliasLabel(alias) : expression,
				fieldtype: "Data",
				reqd: 0,
				source: { kind: "expression", fieldname: alias || undefined, expression },
			});
		}
	}
	return schema;
}

export function validateOutputFields(rows, shape, groupBy = "") {
	const errors = [];
	const list = Array.isArray(rows) ? rows : [];
	const hasAggregate = list.some((row) => row.kind === "function");
	const hasRegularField = list.some((row) => ["field", "raw"].includes(row.kind));

	if (hasAggregate && hasRegularField && !String(groupBy || "").trim()) {
		errors.push(
			"Aggregate functions mixed with regular fields require Group By. Configure Group By under Retrieval Settings, or remove regular output fields."
		);
	}
	const outputNames = new Set();
	if (!list.length) errors.push("Add at least one output field.");
	if (list.some((row) => row.kind === "literal") && !list.some((row) => row.kind !== "literal")) {
		errors.push("Literal columns must be paired with at least one source field or aggregate.");
	}
	if (shape === RESULT_SHAPES.embeddedChildren && !list.some((row) => row.kind === "child")) {
		errors.push("Embedded children requires at least one child-table selection.");
	}
	for (const [index, row] of list.entries()) {
		const prefix = "Output field " + (index + 1) + ": ";
		if (row.kind === "field") {
			const fieldPath = String(row.field ?? "").trim();
			const fieldAlias = String(row.alias ?? "").trim();
			if (!fieldPath) errors.push(prefix + "select a field.");
			else if (fieldPath.split(".").length > 2) {
				errors.push(
					prefix +
						"Frappe v15 supports only one-level Link or child-table field paths in this selection."
				);
			}
			if (fieldAlias && !ALIAS_PATTERN.test(fieldAlias)) {
				errors.push(
					prefix +
						"alias must be lowercase snake_case: start with a letter and use lowercase letters, numbers, and single underscores between words."
				);
			}
		} else if (row.kind === "function") {
			const fn = String(row.functionName ?? "").toLowerCase();
			const field = String(row.field ?? "").trim();
			const alias = String(row.alias ?? "").trim();
			if (!AGGREGATE_SET.has(fn)) errors.push(prefix + "choose a supported function.");
			if (!field) errors.push(prefix + "select a field for the function.");
			else if (field.includes(".")) {
				errors.push(
					prefix +
						"aggregate functions currently support root DocType fields only; child/link aggregates need backend support."
				);
			}
			if (!alias) errors.push(prefix + "enter an output alias for the function.");
			else if (!ALIAS_PATTERN.test(alias)) {
				errors.push(
					prefix +
						"alias must start with a letter or underscore and contain only letters, numbers, and underscores."
				);
			}
		} else if (row.kind === "child") {
			if (!String(row.tableField ?? "").trim()) errors.push(prefix + "select a child table.");
			if (!Array.isArray(row.fields) || !row.fields.length) {
				errors.push(prefix + "select at least one child field.");
			}
		} else if (row.kind === "literal") {
			const fieldname = String(row.fieldname ?? "").trim();
			if (!fieldname) errors.push(prefix + "enter an output field name.");
			else if (!ALIAS_PATTERN.test(fieldname)) {
				errors.push(prefix + "output field name must be lowercase snake_case.");
			}
			if (!String(row.label ?? "").trim()) errors.push(prefix + "enter a label.");
			const fieldtype = String(row.fieldtype || "Data");
			if (
				![
					"Data",
					"Int",
					"Float",
					"Currency",
					"Check",
					"Date",
					"Datetime",
					"Time",
					"Link",
					"Select",
				].includes(fieldtype)
			) {
				errors.push(prefix + "choose a supported output field type.");
			}
			if (["Link", "Select"].includes(fieldtype) && !String(row.options || "").trim()) {
				errors.push(prefix + "enter Options for this field type.");
			}
			const valueSpec = row.value_spec;
			if (
				!isObject(valueSpec) ||
				!["static", "variable", "resolver", "expression"].includes(
					String(valueSpec.mode || "").toLowerCase()
				)
			) {
				errors.push(prefix + "configure a valid FlexValue value.");
			}
		} else if (row.kind === "raw" && !String(row.expression ?? "").trim()) {
			errors.push(prefix + "enter a field expression.");
		}

		const rowNames = [];
		if (row.kind === "literal") {
			rowNames.push(String(row.fieldname ?? "").trim());
		} else if (row.kind === "field") {
			rowNames.push(String(row.alias || row.field || "").trim());
		} else if (row.kind === "function") {
			rowNames.push(String(row.alias || "").trim());
		} else if (row.kind === "child") {
			const tableField = String(row.tableField || "").trim();
			if (tableField) {
				rowNames.push(tableField);
				for (const childField of Array.isArray(row.fields) ? row.fields : []) {
					rowNames.push(tableField + "." + childField);
				}
			}
		} else if (row.kind === "raw") {
			const expression = String(row.expression ?? "").trim();
			const match = expression.match(/^.+?\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$/i);
			if (match) rowNames.push(match[1]);
		}
		for (const outputName of rowNames.filter(Boolean)) {
			if (outputNames.has(outputName)) {
				errors.push(prefix + "Output field '" + outputName + "' is already used.");
			} else {
				outputNames.add(outputName);
			}
		}
	}
	return errors;
}
