/**
 * useControlContext — Dependency injection layer for FlexiRule controls.
 *
 * ## Purpose
 * Replaces all direct `window.frappe.query_report` lookups inside controls
 * with a clean, injectable context. Parent components (QueryRecordsConfig,
 * FilterGroup, etc.) call `provideControlContext()` to expose a local value
 * resolver that child controls can consume without knowing where they are
 * rendered.
 *
 * ## Architecture
 * - Provider:  `provideControlContext(resolver)` — called by parent
 * - Consumer:  `useControlContext()` — called by any control
 *
 * The resolver is a plain function: `(fieldname) => value`
 * It answers the question: "Given a field name that this control's `df.options`
 * points to, what is its current value?"
 *
 * For example, when a Dynamic Link's `df.options = "party_type"`, the control
 * calls `resolver("party_type")` and gets back "Customer" (or whatever the
 * parent filter/form currently has).
 *
 * ## Fallback
 * If no provider exists in the component tree, `useControlContext()` returns
 * a context that falls back to `window.frappe.query_report.get_filter_value()`
 * for backward compatibility with controls rendered outside the Rule Builder
 * (e.g., in native Frappe forms or standalone dialogs).
 */
import { provide, inject, computed, unref } from "vue";

const CONTROL_CONTEXT_KEY = Symbol("fxr-control-context");

/**
 * @typedef {Object} ControlContext
 * @property {(fieldname: string) => any} getFieldValue
 *   Resolve the current value of a sibling/parent field by fieldname.
 * @property {boolean} isProvided
 *   `true` when a parent explicitly provided a context (i.e., we are inside
 *   the Rule Builder). `false` means we are using the global Frappe fallback.
 */

/**
 * Provide a control context to all child components.
 *
 * Call this in a parent component that owns the "form" or "filter set"
 * that controls need to read sibling values from.
 *
 * @param {Object} options
 * @param {Function} options.getFieldValue - `(fieldname: string) => any`
 *   Returns the current value for the given field name. The returned value
 *   should be the *resolved* primitive (e.g., "Customer"), not a structured
 *   `{ mode, value }` wrapper.
 */
export function provideControlContext({ getFieldValue }) {
	const ctx = {
		getFieldValue: getFieldValue || (() => undefined),
		isProvided: true,
	};
	provide(CONTROL_CONTEXT_KEY, ctx);
	return ctx;
}

/**
 * Inject the control context from the nearest provider.
 *
 * If no provider exists, returns a fallback context that delegates to
 * `window.frappe.query_report.get_filter_value()` for backward compatibility.
 *
 * @returns {ControlContext}
 */
export function useControlContext() {
	const ctx = inject(CONTROL_CONTEXT_KEY, null);
	if (ctx) return ctx;

	// Fallback: global Frappe query_report API (for controls outside Rule Builder)
	return {
		getFieldValue(fieldname) {
			if (
				window.frappe &&
				window.frappe.query_report &&
				typeof window.frappe.query_report.get_filter_value === "function"
			) {
				return window.frappe.query_report.get_filter_value(fieldname);
			}
			return undefined;
		},
		isProvided: false,
	};
}

/**
 * Resolve the target DocType for a Dynamic Link field.
 *
 * Handles the standard Frappe pattern where `df.options` contains the
 * fieldname of the "parent" field whose value is the target DocType.
 *
 * @param {Object} df - Field definition
 * @param {ControlContext} ctx - The injected control context
 * @param {Object} [doc] - Optional document object (for form-level resolution)
 * @returns {string} The resolved DocType name, or empty string
 */
export function resolveDynamicLinkDoctype(df, ctx, doc = null) {
	if (!df || !df.options) return "";

	// 1. Try document-level resolution first (standard Frappe form pattern)
	if (doc && doc[df.options]) {
		return String(doc[df.options]);
	}

	// 2. Use the injected context
	const contextVal = ctx.getFieldValue(df.options);
	if (contextVal !== undefined && contextVal !== null && contextVal !== "") {
		// Handle structured values from FlexValueControl
		if (typeof contextVal === "object" && contextVal.mode === "static") {
			return String(contextVal.value || "");
		}
		if (typeof contextVal === "string") {
			return contextVal;
		}
	}

	return "";
}

/**
 * Resolve the target DocType for Link-like fields (Link, Dynamic Link,
 * MultiSelectList).
 *
 * Consolidates the duplicated resolution logic that was previously spread
 * across FlexValueControl, MultiSelectList, ComboBoxControl, and
 * ControlRegistry.
 *
 * @param {Object} df - Field definition
 * @param {ControlContext} ctx - The injected control context
 * @param {Object} [opts] - Additional options
 * @param {Object} [opts.doc] - Document object
 * @param {string} [opts.explicitDoctype] - Explicitly provided doctype prop
 * @returns {string} The resolved DocType name
 */
export function resolveTargetDoctype(df, ctx, opts = {}) {
	if (!df) return opts.explicitDoctype || "";

	// Explicit doctype prop always wins
	if (opts.explicitDoctype) return opts.explicitDoctype;

	const ft = df.fieldtype;

	// Standard Link: df.options IS the DocType
	if (ft === "Link") {
		return df.options || "";
	}

	// Dynamic Link: df.options is a fieldname pointing to the DocType
	if (ft === "Dynamic Link") {
		return resolveDynamicLinkDoctype(df, ctx, opts.doc);
	}

	// MultiSelectList / MultiSelect: df.options may be a DocType name or
	// a fieldname referencing a parent filter
	if (["MultiSelectList", "MultiSelect", "MultiCheck"].includes(ft)) {
		const optsStr = df.options;
		if (!optsStr || typeof optsStr !== "string") return "";

		// If contains delimiters, it's static options, not a DocType
		if (optsStr.includes("\n") || optsStr.includes(",") || optsStr.includes(";")) {
			return "";
		}

		// Try resolving as a parent field reference first
		const parentVal = ctx.getFieldValue(optsStr);
		if (parentVal) {
			if (typeof parentVal === "object" && parentVal.mode === "static") {
				return String(parentVal.value || "");
			}
			if (typeof parentVal === "string") {
				return parentVal;
			}
		}

		// If it's not a self-reference, treat as a DocType name
		if (optsStr !== df.fieldname) {
			return optsStr;
		}

		return "";
	}

	return df.options || "";
}
