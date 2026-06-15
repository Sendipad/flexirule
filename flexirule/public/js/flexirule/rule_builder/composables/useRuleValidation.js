import { ref, computed } from "vue";
import { getContract } from "../core/contracts";

export function useRuleValidation(nodes) {
	const validation_errors = ref([]);

	async function validateRule(ruleDoc) {
		const errors = [];
		const nodesList = nodes.value || [];

		for (const node of nodesList) {
			if (node.type === "start") continue;

			const label = node.data?.action_label || node.label || node.id;

			if (node.type === "selector") {
				errors.push(`${label}: ${__("Please configure this action type before saving")}`);
				continue;
			}

			const doc = node.data;

			// Deep sync condition_json for validation if missing
			if (doc.action_type === "Condition" && !doc.condition_json && doc.config) {
				doc.condition_json = JSON.stringify(doc.config);
			}

			// Auto-populate hidden mandatory fields
			if (["Document Action", "Assignment", "Notify"].includes(doc.action_type)) {
				if (doc.action_type === "Document Action" && !doc.permission_audit_reason) {
					doc.permission_audit_reason = "System Rule Execution";
				}
				if (!doc.reference_doctype) {
					doc.reference_doctype = ruleDoc.document_type;
				}
			}

			// Contract-based validation
			const { validateAgainstContract } = await import("../core/contracts");
			const contractValidation = validateAgainstContract(doc);
			if (!contractValidation.valid) {
				contractValidation.errors.forEach((err) => {
					errors.push(`${label}: ${err}`);
				});
			}
		}

		validation_errors.value = errors;
		return {
			valid: errors.length === 0,
			errors,
		};
	}

	return {
		validation_errors,
		validateRule,
	};
}
