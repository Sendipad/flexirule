/**
 * Pure ES module for building, normalizing, ranking, and searching the FlexValue source catalogue.
 * Supports document fields, variables, and context-aware resolvers with multi-property search and Frappe translations.
 */

export function cleanFriendlyLabel(label, value) {
	if (!label) return value || "";
	const parenMatch = String(label).match(/\(([^)]+)\)/);
	if (parenMatch && parenMatch[1]) {
		return parenMatch[1].trim();
	}
	return String(label).replace(/^(doc|old_doc|vars|caller|rule)\./, "");
}

/**
 * Normalizes document fields and variables into standard catalogue items.
 */
export function buildSourceCatalogue({
	docFields = [],
	variableOptions = [],
	resolvers = [],
	fieldType = "Data",
	allowedResolverKinds = null,
	currentDocType = "",
	translate = (s) => (globalThis.__ ? globalThis.__(s) : s),
} = {}) {
	const catalogue = [];
	const seenKeys = new Set();

	// 1. Process Document Fields
	for (const f of docFields) {
		// Prefer the qualified value when present (e.g. "old_doc.status", "caller.user", "rule.id")
		// rather than f.fieldname ("status") which would incorrectly default to "doc.status".
		const rawVal = f.value || f.fieldname || f.id || "";
		if (!rawVal) continue;

		// Preserve already-qualified scopes (e.g. old_doc.status, vars.total, item.qty)
		const strVal = String(rawVal).startsWith("@")
			? String(rawVal).substring(1)
			: String(rawVal);
		const parts = strVal.split(".").filter(Boolean);
		const knownScopes = new Set([
			"doc",
			"old_doc",
			"vars",
			"caller",
			"rule",
			"doctype",
			"row",
			"item",
			"loop",
		]);

		let scope = "doc";
		let segments = parts;
		if (knownScopes.has(parts[0])) {
			scope = parts[0];
			segments = parts.slice(1);
		} else if (parts.length > 1) {
			scope = parts[0];
			segments = parts.slice(1);
		}

		const canonicalPath = segments.length ? `${scope}.${segments.join(".")}` : scope;
		// Deduplicate strictly by canonical identity
		const canonicalKey = `path:${canonicalPath}`;
		if (seenKeys.has(canonicalKey)) continue;
		seenKeys.add(canonicalKey);

		const rawLabel =
			f.label || (segments.length ? segments[segments.length - 1] : canonicalPath);
		const translatedLabel = translate(rawLabel);

		catalogue.push({
			id: canonicalPath,
			sourceType: scope === "doc" ? "field" : "variable",
			category: scope === "doc" ? "fields" : "variables",
			categoryLabel: scope === "doc" ? translate("Document Fields") : translate("Variables"),
			icon: scope === "doc" ? "fa fa-file-text-o" : "fa fa-cube",
			primaryLabel: translatedLabel || rawLabel,
			rawLabel: rawLabel,
			secondaryText: canonicalPath,
			canonicalPath: canonicalPath,
			fieldname: segments.length ? segments[segments.length - 1] : null,
			fieldtype: f.fieldtype || "Data",
			options: f.options || null,
			searchTerms: [
				canonicalPath.toLowerCase(),
				strVal.toLowerCase(),
				segments.join(".").toLowerCase(),
				rawLabel.toLowerCase(),
				(translatedLabel || "").toLowerCase(),
				cleanFriendlyLabel(rawLabel, canonicalPath).toLowerCase(),
			],
			payload: {
				mode: "variable",
				path: { scope, segments },
			},
		});
	}

	// 2. Process Variables
	for (const v of variableOptions) {
		const val = v.value || v.id || v;
		if (!val) continue;
		const rawPath = String(val).startsWith("@") ? String(val).substring(1) : String(val);
		const parts = rawPath.split(".").filter(Boolean);
		const knownScopes = new Set([
			"doc",
			"old_doc",
			"vars",
			"caller",
			"rule",
			"doctype",
			"row",
			"item",
			"loop",
		]);
		const scope = knownScopes.has(parts[0]) ? parts[0] : parts.length > 1 ? parts[0] : "doc";
		const segments = knownScopes.has(parts[0]) || parts.length > 1 ? parts.slice(1) : parts;
		const canonicalPath = segments.length ? `${scope}.${segments.join(".")}` : scope;

		// Deduplicate strictly by canonical identity across both fields and variableOptions
		const canonicalKey = `path:${canonicalPath}`;
		if (seenKeys.has(canonicalKey)) continue;
		seenKeys.add(canonicalKey);

		const rawLabel = v.label || cleanFriendlyLabel(v.friendlyLabel || rawPath, rawPath);
		const translatedLabel = translate(rawLabel);

		catalogue.push({
			id: canonicalPath,
			sourceType: scope === "doc" ? "field" : "variable",
			category: scope === "doc" ? "fields" : "variables",
			categoryLabel: scope === "doc" ? translate("Document Fields") : translate("Variables"),
			icon: scope === "doc" ? "fa fa-file-text-o" : "fa fa-cube",
			primaryLabel: translatedLabel || rawLabel,
			rawLabel: rawLabel,
			secondaryText: canonicalPath,
			canonicalPath: canonicalPath,
			scope: scope,
			segments: segments,
			fieldtype: v.fieldtype || null,
			searchTerms: [
				rawPath.toLowerCase(),
				canonicalPath.toLowerCase(),
				segments.join(".").toLowerCase(),
				rawLabel.toLowerCase(),
				(translatedLabel || "").toLowerCase(),
				cleanFriendlyLabel(rawLabel, rawPath).toLowerCase(),
			],
			payload: {
				mode: "variable",
				path: { scope, segments },
			},
		});
	}

	// 3. Process Resolvers
	for (const r of resolvers) {
		const kind = r.kind || r.id;
		if (!kind) continue;
		const key = `resolver:${kind}`;
		if (seenKeys.has(key)) continue;
		seenKeys.add(key);

		const rawLabel = r.label || kind;
		const translatedLabel = translate(rawLabel);
		const description = r.description ? translate(r.description) : "";
		const rawDescription = r.description || "";

		// Context compatibility with normalization for legacy "fetch" and canonical "lookup"
		const normalizedAllowed = Array.isArray(allowedResolverKinds)
			? allowedResolverKinds.map((k) => (k === "fetch" ? "lookup" : k))
			: null;
		const normalizedKind = kind === "fetch" ? "lookup" : kind;
		const isKindAllowed = !normalizedAllowed || normalizedAllowed.includes(normalizedKind);
		const isCompatible = isKindAllowed;

		catalogue.push({
			id: kind,
			sourceType: "resolver",
			category: "resolvers",
			categoryLabel: translate("Resolvers"),
			icon: r.icon || "fa fa-bolt",
			primaryLabel: translatedLabel || rawLabel,
			rawLabel: rawLabel,
			secondaryText: r.operation ? `${kind}.${r.operation}` : kind,
			kind: kind,
			family:
				r.family ||
				(kind === "math_formula" ? "math" : kind === "lookup" ? "lookup" : kind),
			operation:
				r.operation ||
				(kind === "math_formula" ? "formula" : kind === "lookup" ? "fetch" : "calculate"),
			description: description,
			isCompatible: isCompatible,
			searchTerms: [
				kind.toLowerCase(),
				(r.family || "").toLowerCase(),
				(r.operation || "").toLowerCase(),
				rawLabel.toLowerCase(),
				(translatedLabel || "").toLowerCase(),
				description.toLowerCase(),
				rawDescription.toLowerCase(),
			],
			payload: {
				mode: "resolver",
				kind: kind,
				family: r.family,
				operation: r.operation,
				config: r.defaultConfig || {},
			},
		});
	}

	return catalogue;
}

/**
 * Searches and scores items from the catalogue.
 * Exact prefix on primaryLabel or canonicalPath scores highest, followed by exact word matches, substring matches.
 */
export function searchSourceCatalogue(catalogue, query = "", { preferredFieldType = null } = {}) {
	const q = query.trim().toLowerCase();
	if (!q) {
		// Return all items grouped with compatible resolvers first
		return sortCatalogueItems([...catalogue], preferredFieldType);
	}

	const scored = [];
	for (const item of catalogue) {
		let bestScore = 0;
		for (const term of item.searchTerms) {
			if (!term) continue;
			if (term === q) {
				bestScore = Math.max(bestScore, 100);
			} else if (term.startsWith(q)) {
				bestScore = Math.max(bestScore, 80);
			} else if (term.includes(` ${q}`) || term.includes(`.${q}`) || term.includes(`_${q}`)) {
				bestScore = Math.max(bestScore, 60);
			} else if (term.includes(q)) {
				bestScore = Math.max(bestScore, 40);
			}
		}

		if (bestScore > 0) {
			// Compatibility boost
			if (item.sourceType === "resolver") {
				if (item.isCompatible) bestScore += 10;
				else bestScore -= 20;
			}
			scored.push({ item, score: bestScore });
		}
	}

	scored.sort((a, b) => {
		if (b.score !== a.score) return b.score - a.score;
		return a.item.primaryLabel.localeCompare(b.item.primaryLabel);
	});

	return scored.map((s) => s.item);
}

function sortCatalogueItems(items, preferredFieldType) {
	return items.sort((a, b) => {
		// Category order: fields -> variables -> resolvers
		const catOrder = { fields: 1, variables: 2, resolvers: 3 };
		const aOrder = catOrder[a.category] || 99;
		const bOrder = catOrder[b.category] || 99;
		if (aOrder !== bOrder) return aOrder - bOrder;

		if (a.sourceType === "resolver" && b.sourceType === "resolver") {
			if (a.isCompatible !== b.isCompatible) {
				return a.isCompatible ? -1 : 1;
			}
		}
		return a.primaryLabel.localeCompare(b.primaryLabel);
	});
}
