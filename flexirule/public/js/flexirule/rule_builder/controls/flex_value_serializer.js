/**
 * Authoritative serialization and deserialization functions for FlexValue payloads.
 */

export function escapeAttr(str) {
	return String(str || "")
		.replace(/&/g, "&amp;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
}

export function escapeHtml(str) {
	return String(str || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

export function isVariableSyntax(val) {
	return (
		typeof val === "string" &&
		(val.startsWith("@") || val.startsWith("doc.") || val.startsWith("vars."))
	);
}

export function coerceStructuredValue(val, currentFieldType = "Data") {
	if (val && typeof val === "object") {
		if (val.mode === "static") {
			return {
				mode: "static",
				value_type: val.value_type || currentFieldType,
				value: val.value,
			};
		}
		if (val.mode === "variable") {
			const rawPath = val.path || {};
			const scope =
				rawPath.scope || (typeof rawPath === "string" ? rawPath.split(".")[0] : "doc");
			const segments = Array.isArray(rawPath.segments)
				? rawPath.segments
				: typeof rawPath === "string"
				? rawPath.split(".").slice(1)
				: [];
			return {
				mode: "variable",
				path: { scope, segments },
			};
		}
		if (val.mode === "resolver") {
			const rawConfig = val.config || {};
			let family = val.family || rawConfig.family;
			let operation = val.operation || rawConfig.operation;
			let config = rawConfig;

			if (!family) {
				if (rawConfig.kind === "math_formula") {
					family = "math";
					operation = operation || "formula";
				} else if (
					rawConfig.kind === "collection" ||
					rawConfig.kind === "child_aggregation"
				) {
					family = "collection";
					operation = operation || rawConfig.operation || rawConfig.agg_op || "any";
				} else if (rawConfig.kind === "lookup" || rawConfig.kind === "fetch") {
					family = "lookup";
					operation = operation || "fetch";
				} else if (rawConfig.kind === "system_context") {
					family = "system_context";
					operation = operation || "get";
				} else if (rawConfig.kind) {
					family = rawConfig.kind;
				}
			}

			if (config.config && typeof config.config === "object") {
				config = config.config;
			}

			return {
				mode: "resolver",
				family: family || "text",
				operation: operation || "combine",
				value_type: val.value_type || currentFieldType,
				config,
			};
		}
		if (val.mode === "template") {
			return { mode: "template", segments: Array.isArray(val.segments) ? val.segments : [] };
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
		const displayPath =
			structured.path?.scope && structured.path?.segments?.length
				? `${structured.path.scope}.${structured.path.segments.join(".")}`
				: String(structured.path || "");
		return `<span data-token-type="variable" data-path="${escapeAttr(
			displayPath
		)}" data-label=""></span>`;
	}

	if (structured.mode === "resolver") {
		return `<span data-token-type="resolver" data-family="${escapeAttr(
			structured.family || ""
		)}" data-operation="${escapeAttr(
			structured.operation || ""
		)}" data-expression="${escapeAttr(
			structured.value || ""
		)}" data-label="" data-config='${escapeAttr(
			JSON.stringify(structured.config || null)
		)}'></span>`;
	}

	if (structured.mode === "template" && Array.isArray(structured.segments)) {
		return structured.segments
			.map((segment) => {
				if (!segment || typeof segment !== "object") return "";
				if (segment.type === "text") return escapeHtml(segment.value || "");
				if (segment.type === "value" && segment.value) {
					return deserializeFlexValue(segment.value, currentFieldType);
				}
				return "";
			})
			.join("");
	}

	if (structured.mode === "expression" && Array.isArray(structured.value)) {
		return structured.value
			.map((item) => {
				const typeName = item.type?.name || item.type;
				if (typeName === "text") return escapeHtml(item.value || "");
				if (typeName === "variableToken")
					return `<span data-token-type="variable" data-path="${escapeAttr(
						item.attrs?.path
					)}" data-label="${escapeAttr(item.attrs?.label)}"></span>`;
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

	return escapeHtml(structured.value ?? "");
}

export function serializeContentNodes(content, currentFieldType = "Data") {
	if (!Array.isArray(content) || content.length === 0) {
		return { mode: "static", value_type: currentFieldType, value: "" };
	}

	if (content.length === 1 && content[0].type !== "text") {
		const node = content[0];
		const typeName = node.type?.name || node.type;
		if (typeName === "variableToken") {
			const rawPath = String(node.attrs?.path || "");
			const parts = rawPath.split(".");
			const scope = parts[0] || "doc";
			const segments = parts.slice(1);
			return {
				mode: "variable",
				path: { scope, segments },
			};
		}
		if (typeName === "resolverToken") {
			const config = node.attrs?.config || {};
			const family =
				node.attrs?.family ||
				config.family ||
				(config.kind === "math_formula" ? "math" : config.kind) ||
				"text";
			const operation =
				node.attrs?.operation ||
				config.operation ||
				(family === "math" ? "formula" : config.kind === "lookup" ? "fetch" : "combine");
			const innerConfig =
				config.config && typeof config.config === "object" ? config.config : config;
			return {
				mode: "resolver",
				family,
				operation,
				value_type: currentFieldType,
				config: innerConfig,
			};
		}
	}

	const segments = content.map((item) => {
		const typeName = item.type?.name || item.type;
		if (typeName === "text") {
			return { type: "text", value: item.text || "" };
		}
		if (typeName === "variableToken") {
			const rawPath = String(item.attrs?.path || "");
			const parts = rawPath.split(".");
			const scope = parts[0] || "doc";
			const segs = parts.slice(1);
			return {
				type: "value",
				value: {
					mode: "variable",
					path: { scope, segments: segs },
				},
			};
		}
		if (typeName === "resolverToken") {
			const cfg = item.attrs?.config || {};
			const fam =
				item.attrs?.family ||
				cfg.family ||
				(cfg.kind === "math_formula" ? "math" : cfg.kind) ||
				"text";
			const op =
				item.attrs?.operation ||
				cfg.operation ||
				(fam === "math" ? "formula" : cfg.kind === "lookup" ? "fetch" : "combine");
			const innerCfg = cfg.config && typeof cfg.config === "object" ? cfg.config : cfg;
			return {
				type: "value",
				value: {
					mode: "resolver",
					family: fam,
					operation: op,
					value_type: currentFieldType,
					config: innerCfg,
				},
			};
		}
		return { type: "text", value: "" };
	});

	return { mode: "template", segments };
}
