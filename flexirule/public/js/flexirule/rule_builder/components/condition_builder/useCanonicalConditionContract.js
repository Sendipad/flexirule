/**
 * Composable for fetching and caching the canonical condition contract from the backend.
 * Uses frappe.call("flexirule.ruleflow.api.get_condition_contract")
 */

import { ref, computed } from "vue";
import { normalizeConditionContract } from "./canonical_condition_contract_normalization.mjs";
export { normalizeConditionContract };

let cachedContract = null;
let fetchPromise = null;

const contractState = ref(null);
const isLoading = ref(false);
const error = ref(null);

export function useCanonicalConditionContract() {
	async function loadContract(force = false) {
		if (cachedContract && !force) {
			contractState.value = cachedContract;
			return cachedContract;
		}

		if (fetchPromise && !force) {
			return fetchPromise;
		}

		isLoading.value = true;
		error.value = null;

		fetchPromise = (async () => {
			try {
				if (typeof frappe === "undefined" || !frappe.call) {
					// In test environments or when frappe is unavailable, check window.__FLEXIRULE_CONTRACT__
					if (typeof window !== "undefined" && window.__FLEXIRULE_CONTRACT__) {
						const normalized = normalizeConditionContract(window.__FLEXIRULE_CONTRACT__);
						if (!normalized) {
							throw new Error("Canonical condition contract is incomplete or invalid");
						}
						cachedContract = normalized;
						contractState.value = normalized;
						return normalized;
					}
					// Fail closed when no contract is available
					const err = new Error(
						"Canonical condition contract is unavailable (frappe.call not found)"
					);
					error.value = err.message;
					cachedContract = null;
					contractState.value = null;
					throw err;
				}

				const response = await frappe.call({
					method: "flexirule.ruleflow.api.get_condition_contract",
				});

				const result = response.message || response;
				const normalized = normalizeConditionContract(result);
				if (!normalized) {
					throw new Error("Canonical condition contract is incomplete or invalid");
				}
				cachedContract = normalized;
				contractState.value = normalized;
				return normalized;
			} catch (err) {
				const msg = err?.message || "Failed to load canonical condition contract";
				error.value = msg;
				cachedContract = null;
				contractState.value = null;
				console.error("[FlexiRule] get_condition_contract failed:", err);
				throw err;
			} finally {
				isLoading.value = false;
				fetchPromise = null;
			}
		})();

		return fetchPromise;
	}

	const operators = computed(() => contractState.value?.operators || {});
	const operatorList = computed(() => contractState.value?.operatorList || []);
	const limits = computed(() => contractState.value?.limits || {});
	const flexvalueModes = computed(() => contractState.value?.flexvalue_modes || {});

	return {
		contract: contractState,
		isLoading,
		error,
		loadContract,
		operators,
		operatorList,
		limits,
		flexvalueModes,
	};
}
