import { getStrategy } from "../rule_builder/controls/value_resolver/strategies";
import "../rule_builder/controls/value_resolver/index"; // Ensure strategies are registered

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
export function toDocExpression(field) {
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
 * @param {string} fallbackField - Default field to use if none is specified (deprecated in favor of strategy defaultState)
 * @returns {string} - Python expression wrapped in braces {}
 */
export function compileToCode(item, fallbackField = "") {
	if (!item || !item.kind) return "";

	const strategy = getStrategy(item.kind);
	if (strategy && strategy.compileToCode) {
		return strategy.compileToCode(item);
	}

	// Fallback for legacy calls or missing strategies
	return "";
}

/**
 * Compiles a builder configuration object into a human-readable label.
 *
 * @param {Object} item - The builder configuration item
 * @returns {string} - Human-readable text
 */
export function compileToLabel(item) {
	if (!item || !item.kind) return __("Configure");

	const strategy = getStrategy(item.kind);
	if (strategy && strategy.compileToLabel) {
		return strategy.compileToLabel(item);
	}

	return __("Configure");
}

/**
 * Validates a structured value object used by FlexValueControl and logic nodes.
 *
 * @param {Object} val - The structured value object { mode, value, path, config, segments }
 * @returns {Object} - { valid: boolean, message?: string }
 */
export function validateStructuredValue(val) {
	if (!val || typeof val !== "object" || Array.isArray(val) || !val.mode) {
		const isEmpty = val === undefined || val === null || val === "";
		return { valid: !isEmpty };
	}

	if (val.mode === "static") {
		const isEmpty = val.value === undefined || val.value === null || val.value === "";
		return { valid: !isEmpty, message: isEmpty ? __("Static value is required") : "" };
	}

	if (val.mode === "variable") {
		const hasPath = !!val.path;
		return { valid: hasPath, message: !hasPath ? __("Variable path is required") : "" };
	}

	if (val.mode === "resolver") {
		const hasConfig = !!(val.config && Object.keys(val.config).length > 0);
		const hasValue = !!val.value;
		const isValid = hasConfig || hasValue;
		return {
			valid: isValid,
			message: !isValid ? __("Resolver configuration is required") : "",
		};
	}

	if (val.mode === "expression") {
		const hasSegments = !!(val.value && Array.isArray(val.value) && val.value.length > 0);
		return {
			valid: hasSegments,
			message: !hasSegments ? __("Expression content is required") : "",
		};
	}

	return { valid: true };
}
