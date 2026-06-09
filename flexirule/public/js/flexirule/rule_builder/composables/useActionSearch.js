import { ref, computed, watch } from "vue";
import {
	ACTION_TYPE_CONTRACT,
	PROCESS_REGISTRY,
	getActionTypeOptions,
	getOperationOptions,
	loadContractsFromBackend,
} from "../../core/contracts";

const KEYWORDS_REGISTRY = {
	Notify: ["email", "mail", "notification", "alert", "message", "send"],
	"Assignment:set": ["set", "update", "change", "assign"],
	"Assignment:clear": ["clear", "reset", "empty", "remove value", "delete"],
	"Assignment:increment": ["increment", "add", "plus"],
	"Assignment:decrement": ["decrement", "subtract", "minus"],
	Loop: ["foreach", "iterate", "collection", "items", "repeat"],
	Condition: ["if", "else", "branch", "check"],
	"Query Records": ["find", "search", "get", "fetch", "list", "lookup", "query"],
	"Document Action": ["create", "update", "delete", "todo", "comment", "record", "doc"],
	Stop: ["end", "finish", "terminate", "exit", "success", "error"],
	Wait: ["delay", "pause", "sleep", "timer"],
	"Sub-Rule": ["call", "invoke", "execute", "subroutine"],
	"Process:create_invoice": ["invoice", "billing", "sale"],
	"Process:validate_customer": ["validate", "customer", "verify", "check"],
};

function normalize(value) {
	return String(value || "")
		.toLowerCase()
		.trim()
		.replace(/[_-]+/g, " ")
		.replace(/\s+/g, " ");
}

function acronym(value) {
	return normalize(value)
		.split(" ")
		.filter(Boolean)
		.map((part) => part[0])
		.join("");
}

function scoreText(text, query) {
	const hay = normalize(text);
	const needle = normalize(query);
	if (!needle) return 1;
	if (!hay) return 0;
	if (hay === needle) return 100;
	if (hay.startsWith(needle)) return 70;
	if (hay.includes(` ${needle}`)) return 60;
	if (hay.includes(needle)) return 45;
	const acr = acronym(hay);
	if (acr.startsWith(needle) || acr.includes(needle)) return 35;
	const terms = needle.split(" ").filter(Boolean);
	if (terms.every((term) => hay.includes(term))) return 25;
	return 0;
}

export function useActionSearch() {
	const searchQuery = ref("");
	const processOperations = ref([]);
	const remoteResults = ref([]);
	const isSearchingRemote = ref(false);
	const canPaste = ref(false);

	async function loadProcessOperations() {
		await loadContractsFromBackend();
		if (Array.isArray(PROCESS_REGISTRY) && PROCESS_REGISTRY.length) {
			processOperations.value = PROCESS_REGISTRY.flatMap((proc) =>
				(proc.operations || [])
					.filter((op) => op.enabled !== 0 && op.visible_in_builder !== 0 && op.func_name)
					.map((op) => ({
						process: proc.name,
						module: proc.module,
						operation: op.func_name,
						label: op.label || op.func_name,
						description: op.description || "",
					}))
			);
			return;
		}
		try {
			const res = await frappe.call({
				method: "flexirule.ruleflow.api.get_all_process_operations",
			});
			processOperations.value = res.message || [];
		} catch (e) {
			processOperations.value = [];
		}
	}

	const debouncedRemoteSearch = flexirule.utils.debounce(async (query) => {
		if (!query || query.length < 2) {
			remoteResults.value = [];
			return;
		}
		isSearchingRemote.value = true;
		try {
			const res = await frappe.call({
				method: "flexirule.ruleflow.api.search_actions",
				args: { query, limit: 20 },
			});
			remoteResults.value = (res.message || []).map((item) => ({
				...item,
				type: item.operation ? "op" : "action",
				score: (item.score || 0) * 0.8, // Slightly de-prioritize remote fuzzy matches
				isRemote: true,
			}));
		} catch (e) {
			remoteResults.value = [];
		} finally {
			isSearchingRemote.value = false;
		}
	}, 300);

	watch(searchQuery, (newVal) => {
		debouncedRemoteSearch(newVal);
	});

	function parseScopedQuery(rawQuery) {
		const query = String(rawQuery || "");
		const startsWithScope = query.startsWith(":");
		if (startsWithScope) {
			const scopedBody = query.slice(1);
			const secondSepIdx = scopedBody.indexOf(":");
			if (secondSepIdx === -1) {
				return {
					scopeTerm: scopedBody.trim(),
					opTerm: "",
					isScoped: false,
					isScopePicker: true,
				};
			}
			return {
				scopeTerm: scopedBody.slice(0, secondSepIdx).trim(),
				opTerm: scopedBody.slice(secondSepIdx + 1).trim(),
				isScoped: true,
				isScopePicker: false,
			};
		}
		const sepIdx = query.indexOf(":");
		if (sepIdx === -1) {
			return {
				scopeTerm: "",
				opTerm: query.trim(),
				isScoped: false,
				isScopePicker: false,
			};
		}
		return {
			scopeTerm: query.slice(0, sepIdx).trim(),
			opTerm: query.slice(sepIdx + 1).trim(),
			isScoped: true,
			isScopePicker: false,
		};
	}

	const actionTypesMetadata = computed(() => {
		try {
			const validTypes = getActionTypeOptions();
			return validTypes
				.filter((t) => t && t !== "Entry Action" && t !== "Start")
				.map((t) => {
					const contract = ACTION_TYPE_CONTRACT[t] || {};
					return {
						label: window.__ ? __(t) : t,
						value: t,
						actionType: t,
						icon: contract.css?.icon || "fa fa-cog",
						color: contract.css?.color || "#6b7280",
						description: contract.description || "",
						category: contract.category || (window.__ ? __("Other") : "Other"),
						keywords: KEYWORDS_REGISTRY[t] || [],
					};
				});
		} catch (e) {
			return [];
		}
	});

	function getActionOperations(actionType) {
		const baseOps = (getOperationOptions(actionType) || []).map((op) => ({
			operation: op.value,
			label: op.label || op.value,
			process_name: actionType === "Process" ? op.process_name || null : null,
			description: op.description || "",
			keywords: KEYWORDS_REGISTRY[`${actionType}:${op.value}`] || [],
		}));
		if (actionType !== "Process") return baseOps;

		const pOps = (processOperations.value || []).map((op) => ({
			operation: op.operation,
			label: op.label || op.operation,
			process_name: op.process,
			description: op.description || "",
			keywords: [],
		}));

		const merged = [];
		const seen = new Set();
		[...baseOps, ...pOps].forEach((op) => {
			const key = `${op.process_name || ""}:${op.operation || ""}`;
			if (!key || seen.has(key)) return;
			seen.add(key);
			merged.push(op);
		});
		return merged;
	}

	function toOperationItem(action, op, score = 0) {
		return {
			key: `op:${action.value}:${op.process_name || ""}:${op.operation}`,
			type: "op",
			score,
			label: `${action.label}: ${
				window.__ ? __(op.label || op.operation) : op.label || op.operation
			}`,
			value: action.value,
			operation: op.operation,
			process_name: op.process_name || null,
			icon: action.icon,
			color: action.color,
			description: op.description || action.description,
		};
	}

	const filteredResults = computed(() => {
		const { scopeTerm, opTerm, isScoped, isScopePicker } = parseScopedQuery(searchQuery.value);
		const results = [];
		const query = opTerm;

		// 1. Handle Scope Picker (query starts with :)
		if (isScopePicker) {
			const scopeMatches = actionTypesMetadata.value
				.map((action) => ({
					action,
					score: Math.max(
						scoreText(action.label, scopeTerm),
						scoreText(action.value, scopeTerm),
						scoreText(action.description, scopeTerm),
						scoreText(action.category, scopeTerm)
					),
				}))
				.filter(({ score }) => !scopeTerm || score > 0)
				.sort((a, b) => b.score - a.score || a.action.label.localeCompare(b.action.label));

			if (!scopeMatches.length) return [];
			results.push({
				type: "header",
				label: window.__ ? __("Action Scope") : "Action Scope",
			});
			scopeMatches.slice(0, 25).forEach(({ action }) => {
				results.push({
					key: `scope:${action.value}`,
					type: "scope_action",
					score: 999,
					label: `${action.label}:`,
					value: action.value,
					actionType: action.value,
					icon: action.icon,
					color: action.color,
					description: (window.__
						? __("Filter operations in {0}")
						: "Filter operations in {0}"
					).replace("{0}", action.label),
				});
			});
			return results;
		}

		// 2. Handle Scoped Search (e.g. "Assignment: clear")
		if (isScoped) {
			const scopedAction = actionTypesMetadata.value.find(
				(a) => scoreText(a.label, scopeTerm) > 0 || scoreText(a.value, scopeTerm) > 0
			);
			if (!scopedAction) return [];
			results.push({ type: "header", label: scopedAction.label });
			const ops = getActionOperations(scopedAction.value)
				.map((op) => ({
					op,
					score: Math.max(
						scoreText(op.label || op.operation, query),
						scoreText(op.operation, query),
						...(op.keywords || []).map((k) => scoreText(k, query) * 0.8)
					),
				}))
				.filter(({ score }) => !query || score > 0)
				.sort((a, b) => b.score - a.score || a.op.label.localeCompare(b.op.label))
				.slice(0, 30)
				.map(({ op, score }) => toOperationItem(scopedAction, op, score));
			return [...results, ...ops];
		}

		// 3. Global Search
		// Match Action Types
		const actionMatches = actionTypesMetadata.value
			.map((action) => {
				const scores = [
					scoreText(action.label, query),
					scoreText(action.value, query),
					scoreText(action.description, query) * 0.9,
				];
				if (action.keywords) {
					action.keywords.forEach((k) => scores.push(scoreText(k, query) * 0.95));
				}
				return { action, score: Math.max(...scores) };
			})
			.filter(({ score }) => !query || score > 0)
			.sort((a, b) => b.score - a.score || a.action.label.localeCompare(b.action.label));

		// Match Operations (Direct Discovery)
		const opMatches = [];
		if (query) {
			actionTypesMetadata.value.forEach((action) => {
				getActionOperations(action.value).forEach((op) => {
					const scores = [
						scoreText(op.label || op.operation, query),
						scoreText(op.operation, query),
						scoreText(op.description, query) * 0.8,
					];
					if (op.keywords) {
						op.keywords.forEach((k) => scores.push(scoreText(k, query) * 0.95));
					}
					const score = Math.max(...scores);
					if (score > 0) {
						opMatches.push({ action, op, score });
					}
				});
			});
		}

		// special case for Paste/Clipboard if query matches
		if (query && (scoreText("paste", query) > 50 || scoreText("clipboard", query) > 50)) {
			results.push({
				key: "paste-discovery",
				type: "paste_discovery",
				score: 100,
				label: window.__ ? __("Paste Action") : "Paste Action",
				description: window.__ ? __("Insert from clipboard") : "Insert from clipboard",
				icon: "fa-paste",
				color: "var(--blue-500, #3b82f6)",
			});
		}

		// Merge remote results if they aren't already represented in local matches
		const seenKeys = new Set();
		const finalActionMatches = [];
		const finalOpMatches = [];

		actionMatches.forEach(({ action, score }) => {
			finalActionMatches.push({
				key: `action:${action.value}`,
				type: "action",
				score,
				label: action.label,
				value: action.value,
				actionType: action.value,
				icon: action.icon,
				color: action.color,
				description: action.description,
			});
			seenKeys.add(action.value);
		});

		opMatches.forEach(({ action, op, score }) => {
			finalOpMatches.push(toOperationItem(action, op, score));
			seenKeys.add(`${action.value}:${op.process_name || ""}:${op.operation}`);
		});

		remoteResults.value.forEach((item) => {
			const key = item.operation
				? `${item.action_type}:${item.process_name || ""}:${item.operation}`
				: item.action_type;
			if (seenKeys.has(key)) return;
			seenKeys.add(key);

			if (item.type === "op") {
				const action = actionTypesMetadata.value.find(
					(a) => a.value === item.action_type
				) || {
					label: item.action_type,
					value: item.action_type,
					icon: "fa-cog",
					color: "#6b7280",
				};
				finalOpMatches.push({
					...item,
					label: `${action.label}: ${window.__ ? __(item.label) : item.label}`,
					icon: action.icon,
					color: action.color,
				});
			} else {
				finalActionMatches.push({
					...item,
					label: window.__ ? __(item.label) : item.label,
					value: item.action_type,
				});
			}
		});

		if (finalActionMatches.length) {
			results.push({ type: "header", label: window.__ ? __("Actions") : "Actions" });
			results.push(...finalActionMatches.sort((a, b) => b.score - a.score).slice(0, 25));
		}

		if (finalOpMatches.length) {
			results.push({ type: "header", label: window.__ ? __("Operations") : "Operations" });
			results.push(...finalOpMatches.sort((a, b) => b.score - a.score).slice(0, 40));
		}

		return results;
	});

	function checkClipboard() {
		try {
			const local = localStorage.getItem("flexirule-clipboard");
			if (local) {
				const parsed = JSON.parse(local);
				canPaste.value = parsed.type === "flexirule-clipboard" && parsed.nodes?.length > 0;
			} else {
				canPaste.value = false;
			}
		} catch (e) {
			canPaste.value = false;
		}
	}

	return {
		searchQuery,
		filteredResults,
		processOperations,
		isSearchingRemote,
		canPaste,
		loadProcessOperations,
		checkClipboard,
	};
}
