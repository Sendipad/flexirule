/**
 * condition_contract_client.mjs
 * Client wrapper for fetching the canonical condition & FlexValue contract from the backend API.
 */

let cachedContract = null;
let contractPromise = null;

/**
 * Fetches the canonical condition contract from flexirule.ruleflow.api.get_condition_contract.
 *
 * @param {Object} options
 * @param {boolean} [options.forceRefresh=false] - Whether to bypass cache.
 * @returns {Promise<Object>} Resolves with the condition contract payload or throws error.
 */
export async function fetchConditionContract(options = {}) {
	const { forceRefresh = false } = options;

	if (cachedContract && !forceRefresh) {
		return cachedContract;
	}

	if (contractPromise && !forceRefresh) {
		return contractPromise;
	}

	contractPromise = (async () => {
		try {
			const response = await frappe.call({
				method: "flexirule.ruleflow.api.get_condition_contract",
			});

			const contract = response?.message;
			if (!contract || !Array.isArray(contract.operators)) {
				throw new Error("Invalid condition contract structure returned by backend.");
			}

			cachedContract = contract;
			return cachedContract;
		} catch (err) {
			cachedContract = null;
			throw err;
		} finally {
			contractPromise = null;
		}
	})();

	return contractPromise;
}

/**
 * Returns the synchronously cached contract if available, otherwise null.
 */
export function getCachedConditionContract() {
	return cachedContract;
}

/**
 * Resets the in-memory contract cache (useful for testing or error retries).
 */
export function resetContractCache() {
	cachedContract = null;
	contractPromise = null;
}
