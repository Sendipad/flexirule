/**
 * Action Node Presentation Summary Formatter
 *
 * Provides deterministic, concise presentation summary items for canvas cards
 * across all Action Types without altering serialized rule JSON or execution state.
 */

import { getContract, normalizeActionType } from "../../core/contracts";

function parseJsonSafe(val, fallback = {}) {
	if (!val) return fallback;
	if (typeof val === "object") return val;
	try {
		return JSON.parse(val);
	} catch (_e) {
		return fallback;
	}
}

/**
 * Derives presentation summary items for an action node.
 * Returns an array of summary objects:
 * [{ icon: string, text: string, type?: 'tag' | 'row' | 'badge', variant?: string }]
 */
export function getActionSummary(data = {}) {
	if (!data || !data.action_type) return [];

	const actionType = normalizeActionType(data.action_type);
	const operation = data.operation || "";
	const config = parseJsonSafe(data.config);
	const items = [];

	switch (actionType) {
		case "Query Records": {
			if (data.reference_doctype) {
				items.push({
					type: "tag",
					icon: "fa-database",
					text: data.reference_doctype,
				});
			}
			if (data.return_variable) {
				items.push({
					type: "row",
					icon: "fa-long-arrow-right",
					text: `vars.${data.return_variable}`,
				});
			}
			break;
		}

		case "Assignment": {
			const assignments = config.assignments || [];
			if (Array.isArray(assignments) && assignments.length > 0) {
				const first = assignments[0];
				if (first && (first.target || first.target_field)) {
					const target = first.target || first.target_field;
					const op = first.operator || first.op || "=";
					const val =
						typeof first.value === "object"
							? first.value?.mode || "..."
							: String(first.value ?? "");
					const summaryText =
						assignments.length > 1
							? `${target} ${op} ${val} (+${assignments.length - 1} more)`
							: `${target} ${op} ${val}`;
					items.push({
						type: "row",
						icon: "fa-sliders",
						text: summaryText,
					});
				}
			} else if (data.target_field) {
				items.push({
					type: "row",
					icon: "fa-crosshairs",
					text: data.target_field,
				});
			}
			if (data.mutation_mode) {
				items.push({
					type: "tag",
					variant: "mutation",
					icon: "fa-bolt",
					text: data.mutation_mode,
				});
			}
			break;
		}

		case "Document Action": {
			if (data.reference_doctype) {
				items.push({
					type: "tag",
					icon: "fa-file-text-o",
					text: data.reference_doctype,
				});
			}
			if (data.return_variable) {
				items.push({
					type: "row",
					icon: "fa-code",
					text: `vars.${data.return_variable}`,
				});
			}
			break;
		}

		case "Process": {
			if (data.reference_doctype) {
				items.push({
					type: "tag",
					icon: "fa-database",
					text: data.reference_doctype,
				});
			}
			if (data.return_variable) {
				items.push({
					type: "row",
					icon: "fa-code",
					text: `vars.${data.return_variable}`,
				});
			}
			break;
		}

		case "Notify": {
			const msg = data.value_template || config.subject || config.message || "";
			if (msg) {
				items.push({
					type: "row",
					icon: "fa-comment-o",
					text: msg.length > 30 ? msg.substring(0, 30) + "..." : msg,
				});
			}
			if (config.recipients) {
				items.push({
					type: "row",
					icon: "fa-envelope-o",
					text: String(config.recipients),
				});
			}
			break;
		}

		case "Raise Error": {
			const errMsg = data.value_template || config.error_title || "";
			if (errMsg) {
				items.push({
					type: "row",
					icon: "fa-exclamation-circle",
					text: errMsg.length > 35 ? errMsg.substring(0, 35) + "..." : errMsg,
				});
			}
			break;
		}

		case "Sub-Rule": {
			const ruleName = data.sub_rule_name || data.rule || config.sub_rule || "";
			if (ruleName) {
				items.push({
					type: "row",
					icon: "fa-cube",
					text: ruleName,
				});
			}
			if (data.return_variable) {
				items.push({
					type: "row",
					icon: "fa-code",
					text: `vars.${data.return_variable}`,
				});
			}
			break;
		}

		case "Wait": {
			const duration = config.duration || data.timeout || "";
			if (duration) {
				items.push({
					type: "row",
					icon: "fa-clock-o",
					text: `${duration}s`,
				});
			}
			break;
		}

		case "Stop": {
			const mode = operation || "Success";
			items.push({
				type: "tag",
				variant: mode === "Error" ? "error" : "success",
				icon: mode === "Error" ? "fa-times-circle" : "fa-check-circle",
				text: mode,
			});
			break;
		}

		default: {
			if (data.reference_doctype) {
				items.push({
					type: "tag",
					icon: "fa-database",
					text: data.reference_doctype,
				});
			}
			if (data.return_variable) {
				items.push({
					type: "row",
					icon: "fa-code",
					text: `vars.${data.return_variable}`,
				});
			}
			break;
		}
	}

	return items;
}

export function useActionSummary() {
	return {
		getActionSummary,
	};
}
