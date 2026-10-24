import { normalizeActionType, getContract } from "../../core/contracts.js";

/**
 * Shared mapper from Action Type (Rule Action value) to VueFlow node type.
 * Keep this as the single mapping source across builder components/store.
 */
export function mapActionTypeToNodeType(actionType) {
	if (!actionType) return "process";
	const normalized = normalizeActionType(actionType);
	const contract = getContract(normalized);

	if (contract && contract.node_type) {
		return contract.node_type;
	}

	// Fallback for legacy types not in contract
	const compact = normalized.toLowerCase().replace(/[^a-z0-9]/g, "");
	if (compact === "selector") return "selector";
	if (compact === "entryaction" || compact === "start") return "start";
	if (compact === "condition") return "condition";
	if (compact === "loop") return "loop";
	if (compact === "wait") return "wait";
	if (compact === "stop") return "stop";
	if (compact === "raiseerror") return "raise-error";
	if (compact === "notify") return "notify";
	if (compact === "subrule") return "sub-rule";
	if (compact === "queryrecords") return "query";
	if (compact === "documentaction") return "documentaction";
	if (compact === "assignment" || compact === "setvalue") return "assignment";

	return "process";
}
