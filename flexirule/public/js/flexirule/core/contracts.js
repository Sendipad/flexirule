/**
 * FlexiRule contract module — frontend mirror of backend DTO.
 *
 * SINGLE SOURCE OF TRUTH: flexirule/ruleflow/core/contracts.py (backend)
 *
 * This module is a thin stateful container. All contract data originates
 * from the backend via `loadContractsFromBackend()` which calls
 * `flexirule.ruleflow.api.get_contract_dto`.
 *
 * Re-exports state and pure policy functions from `./contracts_policy.mjs`.
 */

export * from "./contracts_policy.mjs";
import {
	ACTION_TYPE_CONTRACT,
	ACTION_TYPE_MAP,
	RELEASE_DISABLED_ACTION_TYPES,
	applyContractDto,
} from "./contracts_policy.mjs";

let _contractsLoaded = false;
let _loadPromise = null;

const CONTRACT_CACHE_KEY = "flexirule:contract_dto:v4";

function getCachedContractDto() {
	try {
		const raw = window.sessionStorage?.getItem(CONTRACT_CACHE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (!parsed || typeof parsed !== "object") return null;
		if (typeof parsed.contract_version_hash !== "string" || !parsed.contract_version_hash) {
			return null;
		}
		if (typeof parsed.schema_version !== "string" || !parsed.schema_version) {
			return null;
		}
		return parsed;
	} catch (_error) {
		return null;
	}
}

function setCachedContractDto(dto) {
	try {
		window.sessionStorage?.setItem(CONTRACT_CACHE_KEY, JSON.stringify(dto || {}));
	} catch (_error) {
		// Ignore storage quota failures
	}
}

function isTransientError(err) {
	if (!err) return false;
	if (!err.httpStatus && !err.status) {
		return true;
	}
	const status = err.httpStatus || err.status || 0;
	return (
		status === 0 ||
		status === 408 ||
		status === 429 ||
		status === 502 ||
		status === 503 ||
		status === 504
	);
}

async function sleep(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchContractDtoWithRetry(maxAttempts = 3) {
	let lastError;
	for (let attempt = 1; attempt <= maxAttempts; attempt++) {
		try {
			const response = await frappe.call({
				method: "flexirule.ruleflow.api.get_contract_dto",
			});
			const dto = response?.message;
			if (!dto || typeof dto !== "object") {
				throw new Error("Backend returned an empty or invalid contract DTO.");
			}
			if (!dto.contract_version_hash) {
				throw new Error("Backend contract DTO is missing contract_version_hash.");
			}
			return dto;
		} catch (err) {
			lastError = err;
			if (!isTransientError(err)) {
				throw err;
			}
			if (attempt < maxAttempts) {
				const delay = 500 * Math.pow(2, attempt - 1);
				console.warn(
					`FlexiRule: Contract fetch attempt ${attempt} failed (transient). Retrying in ${delay}ms…`,
					err
				);
				await sleep(delay);
			}
		}
	}
	throw lastError;
}

export async function loadContractsFromBackend(force = false) {
	if (_loadPromise && !force) return _loadPromise;

	_loadPromise = _doLoad(force);
	try {
		await _loadPromise;
	} finally {
		if (!_contractsLoaded) {
			_loadPromise = null;
		}
	}
}

async function _doLoad(force) {
	if (_contractsLoaded && !force) return;
	if (!window.frappe?.call) {
		throw new Error("FlexiRule: frappe.call is not available — contracts cannot be loaded.");
	}

	const bootDto = window.frappe?.boot?.flexirule_contract_dto;
	if (bootDto && typeof bootDto === "object" && bootDto.contract_version_hash && !force) {
		applyContractDto(bootDto);
		setCachedContractDto(bootDto);
		_contractsLoaded = true;
		return;
	}

	const cachedDto = getCachedContractDto();
	if (cachedDto && !force) {
		applyContractDto(cachedDto);
		_contractsLoaded = true;

		fetchContractDtoWithRetry()
			.then((freshDto) => {
				if (freshDto.contract_version_hash !== cachedDto.contract_version_hash) {
					applyContractDto(freshDto);
					setCachedContractDto(freshDto);
				}
			})
			.catch((err) => {
				console.warn("FlexiRule: Background contract refresh failed:", err);
			});
		return;
	}

	const dto = await fetchContractDtoWithRetry();
	applyContractDto(dto);
	setCachedContractDto(dto);
	_contractsLoaded = true;
}

export async function loadProcessScript(processName) {
	if (!processName) return;
	if (window.flexirule?.processes?.[processName]) return;

	try {
		const r = await frappe.call({
			method: "flexirule.ruleflow.doctype.process.process.get_process_script",
			args: { process_name: processName },
		});
		if (r.message && r.message.script) {
			frappe.dom.eval(r.message.script);
		}
	} catch (e) {
		console.warn(`Failed to load script for process ${processName}`, e);
	}
}

export default ACTION_TYPE_CONTRACT;
