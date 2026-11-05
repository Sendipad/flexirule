// Standalone pure serialization & deserialization helpers for FlexValue editor

export function escapeAttr(str) {
	return String(str || "")
		.replace(/&/g, "&amp;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
}

export function unescapeAttr(str) {
	return String(str || "")
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&amp;/g, "&");
}

export function coerceStructuredValue(val, currentFieldType = "Data") {
	if (val && typeof val === "object" && val.mode) {
		if (
			["formula", "math_formula", "format", "normalize", "normalization"].includes(val.mode)
		) {
			const config = { ...(val.config || {}) };
			let family = "text";
			let operation = "combine";
			if (val.mode === "formula" || val.mode === "math_formula") {
				family = "math";
				operation = "formula";
				config.kind = "math_formula";
			} else if (["format", "normalize", "normalization"].includes(val.mode)) {
				family = "text";
				operation = val.mode === "format" ? "format" : "normalize";
				config.kind = "text";
			}
			return {
				mode: "resolver",
				family: val.family || config.family || family,
				operation: val.operation || config.operation || operation,
				value_type: val.value_type || currentFieldType,
				config,
			};
		}
		if (val.mode === "variable") {
			if (val.path && typeof val.path === "object") {
				return {
					mode: "variable",
					path: {
						scope: val.path.scope || "doc",
						segments: Array.isArray(val.path.segments) ? [...val.path.segments] : [],
					},
				};
			}
			const pathStr = String(val.value || val.path || "");
			const parts = pathStr.split(".");
			const scope = parts[0] || "doc";
			const segments = parts.slice(1);
			return {
				mode: "variable",
				path: { scope, segments },
			};
		}
		if (val.mode === "resolver") {
			const config = val.config || {};
			let family = val.family || config.family || config.kind || "text";
			let operation = val.operation || config.operation || "combine";
			if (family === "math_formula" || config.kind === "math_formula") {
				family = "math";
				if (operation === "combine" || !val.operation) {
					operation = "formula";
				}
			}
			if (family === "fetch" || config.kind === "fetch") {
				family = "lookup";
				operation = "fetch";
			}
			if (family === "child_aggregation" || config.kind === "child_aggregation") {
				family = "collection";
			}
			return {
				mode: "resolver",
				family,
				operation,
				value_type: val.value_type || currentFieldType,
				config,
			};
		}
		if (val.mode === "template") {
			return {
				mode: "template",
				segments: Array.isArray(val.segments) ? val.segments : [],
			};
		}
		if (val.mode === "expression") {
			return { mode: "expression", value: Array.isArray(val.value) ? val.value : [] };
		}
		return {
			mode: "static",
			value_type: val.value_type || currentFieldType,
			value: val.value,
		};
	}

	if (val === null || val === undefined) {
		return { mode: "static", value_type: currentFieldType, value: "" };
	}
	return { mode: "static", value_type: currentFieldType, value: val };
}

export function deserializeFlexValue(val, currentFieldType = "Data") {
	if (!val) return "";
	const structured = coerceStructuredValue(val, currentFieldType);

	if (structured.mode === "variable") {
		const pathObj = structured.path || {};
		const scope = pathObj.scope || "doc";
		const segments = Array.isArray(pathObj.segments) ? pathObj.segments : [];
		const pathStr = segments.length ? `${scope}.${segments.join(".")}` : scope;
		return `<span data-token-type="variable" data-path="${escapeAttr(
			pathStr
		)}" data-label=""></span>`;
	}

	if (structured.mode === "resolver") {
		return `<span data-token-type="resolver" data-family="${escapeAttr(
			structured.family || ""
		)}" data-operation="${escapeAttr(
			structured.operation || ""
		)}" data-value-type="${escapeAttr(
			structured.value_type || ""
		)}" data-expression="" data-label="" data-config='${escapeAttr(
			JSON.stringify(structured.config || null)
		)}'></span>`;
	}

	if (structured.mode === "template" && Array.isArray(structured.segments)) {
		return structured.segments
			.map((segment) => {
				if (!segment) return "";
				if (segment.type === "text") {
					return escapeAttr(segment.value || "");
				}
				if (segment.type === "value" && segment.value) {
					const child = coerceStructuredValue(segment.value, currentFieldType);
					if (child.mode === "variable") {
						const pathObj = child.path || {};
						const scope = pathObj.scope || "doc";
						const segments = Array.isArray(pathObj.segments) ? pathObj.segments : [];
						const pathStr = segments.length ? `${scope}.${segments.join(".")}` : scope;
						return `<span data-token-type="variable" data-path="${escapeAttr(
							pathStr
						)}" data-label=""></span>`;
					}
					if (child.mode === "resolver") {
						return `<span data-token-type="resolver" data-family="${escapeAttr(
							child.family || ""
						)}" data-operation="${escapeAttr(
							child.operation || ""
						)}" data-value-type="${escapeAttr(
							child.value_type || ""
						)}" data-config='${escapeAttr(
							JSON.stringify(child.config || null)
						)}'></span>`;
					}
					if (child.mode === "static") {
						return escapeAttr(child.value ?? "");
					}
				}
				return "";
			})
			.join("");
	}

	if (structured.mode === "expression" && Array.isArray(structured.value)) {
		return structured.value
			.map((item) => {
				const typeName = item.type?.name || item.type;
				if (typeName === "text") return escapeAttr(item.value || "");
				if (typeName === "variableToken")
					return `<span data-token-type="variable" data-path="${escapeAttr(
						item.attrs?.path || ""
					)}" data-label="${escapeAttr(item.attrs?.label || "")}"></span>`;
				if (
					["resolverToken", "formulaToken", "normalizeToken", "formatToken"].includes(
						typeName
					)
				) {
					return `<span data-token-type="resolver" data-expression="${escapeAttr(
						item.attrs?.expression || item.attrs?.resolver || ""
					)}" data-label="${escapeAttr(
						item.attrs?.label || ""
					)}" data-config='${escapeAttr(
						JSON.stringify(item.attrs?.config || null)
					)}'></span>`;
				}
				return "";
			})
			.join("");
	}

	return structured.value ?? "";
}
