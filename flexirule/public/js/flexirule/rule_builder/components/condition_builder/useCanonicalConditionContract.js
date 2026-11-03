/**
 * Composable for fetching and caching the canonical condition contract from the backend.
 * Uses frappe.call("flexirule.ruleflow.api.get_condition_contract")
 */

import { ref, computed } from "vue";

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
					const mockContract = {
						api_version: "1",
						operators: {},
						limits: { depth: 16, nodes: 128, path_segments: 8 },
						flexvalue_modes: { static: [], variable: {}, resolver: {}, template: {} },
					};
					cachedContract = mockContract;
					contractState.value = mockContract;
					return mockContract;
				}

				const response = await frappe.call({
					method: "flexirule.ruleflow.api.get_condition_contract",
				});

				const result = response.message || response;
				cachedContract = result;
				contractState.value = result;
				return result;
			} catch (err) {
				const msg = err?.message || "Failed to load canonical condition contract";
				error.value = msg;
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
	const limits = computed(() => contractState.value?.limits || {});
	const flexvalueModes = computed(() => contractState.value?.flexvalue_modes || {});

	return {
		contract: contractState,
		isLoading,
		error,
		loadContract,
		operators,
		limits,
		flexvalueModes,
	};
}
