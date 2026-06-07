<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import {
	ACTION_TYPE_CONTRACT,
	PROCESS_REGISTRY,
	getActionTypeOptions,
	getOperationOptions,
	loadContractsFromBackend,
} from "../../core/contracts";

const props = defineProps({
	active: Boolean,
	position: Object, // { x, y } in pixels relative to viewport or parent
});

const emit = defineEmits(["select", "close"]);

const searchQuery = ref("");
const processOperations = ref([]);
const selectedIndex = ref(-1);
const canPaste = ref(false);

const popoverRef = ref(null);
const searchInputRef = ref(null);

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

const actionTypes = computed(() => {
	try {
		const validTypes = getActionTypeOptions();

		const getTypeMetadata = (t) => {
			const contract = ACTION_TYPE_CONTRACT[t] || {};
			return {
				label: window.__ ? __(t) : t,
				value: t,
				actionType: t,
				icon: contract.css?.icon || "fa fa-cog",
				color: contract.css?.color || "#6b7280",
				description: contract.description || "",
				category: contract.category || (window.__ ? __("Other") : "Other"),
			};
		};

		return validTypes
			.filter((t) => t && t !== "Entry Action" && t !== "Start")
			.map(getTypeMetadata);
	} catch (e) {
		console.error("Error computing actionTypes:", e);
		return [];
	}
});

function getScopedAction(scopeTerm) {
	if (!scopeTerm) return null;
	let best = null;
	let bestScore = 0;
	(actionTypes.value || []).forEach((action) => {
		const score = Math.max(
			scoreText(action.label, scopeTerm),
			scoreText(action.value, scopeTerm),
			scoreText(action.category, scopeTerm),
			scoreText(action.description, scopeTerm)
		);
		if (score > bestScore) {
			bestScore = score;
			best = action;
		}
	});
	return bestScore > 0 ? best : null;
}

function getActionOperations(action) {
	if (!action) return [];
	const baseOps = (getOperationOptions(action.value) || []).map((op) => ({
		operation: op.value,
		label: op.label || op.value,
		process_name: action.value === "Process" ? op.process_name || null : null,
		description: op.description || "",
	}));
	if (action.value !== "Process") return baseOps;

	const processOps = (processOperations.value || []).map((op) => ({
		operation: op.operation,
		label: op.label || op.operation,
		process_name: op.process,
		description: op.description || "",
	}));

	const merged = [];
	const seen = new Set();
	[...baseOps, ...processOps].forEach((op) => {
		const key = `${op.process_name || ""}:${op.operation || ""}`;
		if (!key || seen.has(key)) return;
		seen.add(key);
		merged.push(op);
	});
	return merged;
}

function toActionItem(action, score = 0) {
	return {
		type: "action",
		score,
		label: action.label,
		value: action.value,
		actionType: action.value,
		icon: action.icon,
		color: action.color,
		description: action.description,
	};
}

function toScopeActionItem(action) {
	return {
		type: "scope_action",
		score: 999,
		label: `${action.label}:`,
		value: action.value,
		actionType: action.value,
		icon: action.icon,
		color: action.color,
		description: __("Filter operations in {0}").replace("{0}", action.label),
	};
}

function toOperationItem(action, op, score = 0) {
	return {
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
	try {
		const { scopeTerm, opTerm, isScoped, isScopePicker } = parseScopedQuery(searchQuery.value);
		const results = [];

		if (isScopePicker) {
			const scopeMatches = (actionTypes.value || [])
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
			results.push({ type: "header", label: __("Action Scope") });
			scopeMatches.slice(0, 25).forEach(({ action }) => {
				results.push(toScopeActionItem(action));
			});

			const primaryAction = scopeMatches[0]?.action || null;
			if (primaryAction) {
				const opItems = getActionOperations(primaryAction)
					.map((op) => ({
						op,
						score: Math.max(
							scoreText(op.label || op.operation, scopeTerm),
							scoreText(op.operation, scopeTerm)
						),
					}))
					.filter(({ score }) => !scopeTerm || score > 0)
					.sort((a, b) => b.score - a.score || a.op.label.localeCompare(b.op.label))
					.slice(0, 25)
					.map(({ op, score }) => toOperationItem(primaryAction, op, score));
				if (opItems.length) {
					results.push({
						type: "header",
						label: __("Operations in {0}").replace("{0}", primaryAction.label),
					});
					results.push(...opItems);
				}
			}

			return results;
		}

		if (isScoped) {
			const scopedAction = getScopedAction(scopeTerm);
			if (!scopedAction) return [];
			results.push({ type: "header", label: scopedAction.label });
			results.push(toScopeActionItem(scopedAction));

			const operations = getActionOperations(scopedAction)
				.map((op) => ({
					op,
					score: Math.max(
						scoreText(op.label || op.operation, opTerm),
						scoreText(op.operation, opTerm)
					),
				}))
				.filter(({ score }) => !opTerm || score > 0)
				.sort((a, b) => b.score - a.score || a.op.label.localeCompare(b.op.label))
				.slice(0, 25)
				.map(({ op, score }) => toOperationItem(scopedAction, op, score));

			return [...results, ...operations];
		}

		const query = opTerm;
		const actionMatches = (actionTypes.value || [])
			.map((action) => ({
				action,
				score: Math.max(
					scoreText(action.label, query),
					scoreText(action.value, query),
					scoreText(action.description, query)
				),
			}))
			.filter(({ score }) => !query || score > 0)
			.sort((a, b) => b.score - a.score || a.action.label.localeCompare(b.action.label));

		if (actionMatches.length) {
			results.push({ type: "header", label: __("Actions") });
			actionMatches.slice(0, 25).forEach(({ action, score }) => {
				results.push(toActionItem(action, score));
			});
		}

		if (query) {
			const opMatches = [];
			(actionTypes.value || []).forEach((action) => {
				getActionOperations(action).forEach((op) => {
					const score = Math.max(
						scoreText(op.label || op.operation, query),
						scoreText(op.operation, query)
					);
					if (score > 0) {
						opMatches.push({ action, op, score });
					}
				});
			});
			if (opMatches.length) {
				results.push({ type: "header", label: __("Operations") });
				opMatches
					.sort((a, b) => b.score - a.score || a.op.label.localeCompare(b.op.label))
					.slice(0, 30)
					.forEach(({ action, op, score }) =>
						results.push(toOperationItem(action, op, score))
					);
			}
		}

		return results;
	} catch (e) {
		console.error("Error computing filteredResults:", e);
		return [];
	}
});

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

function selectItem(item) {
	if (item.type === "header") return;
	if (item.type === "scope_action") {
		searchQuery.value = `${item.value}: `;
		selectedIndex.value = -1;
		nextTick(() => searchInputRef.value?.focus());
		return;
	}
	const selection = {
		action_type: item.value || "Process",
		operation: item.operation || null,
		process_name: item.process_name || null,
		label: item.label || item.value || "Process",
	};
	emit("select", selection);
}

function nextSelectableIndex(startIndex, direction) {
	const total = filteredResults.value.length;
	if (!total) return -1;
	let index = startIndex;
	for (let step = 0; step < total; step++) {
		index = (index + direction + total) % total;
		if (filteredResults.value[index]?.type !== "header") return index;
	}
	return -1;
}

function onKeydown(e) {
	if (e.key === "Escape") emit("close");
	if (!filteredResults.value.length) return;

	if (e.key === "ArrowDown") {
		e.preventDefault();
		selectedIndex.value = nextSelectableIndex(selectedIndex.value, 1);
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		selectedIndex.value = nextSelectableIndex(selectedIndex.value, -1);
	} else if (e.key === "Enter" && selectedIndex.value !== -1) {
		e.preventDefault();
		selectItem(filteredResults.value[selectedIndex.value]);
	}
}

function onClickOutside(e) {
	if (popoverRef.value && !popoverRef.value.contains(e.target)) {
		emit("close");
	}
}

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

function onPasteClick() {
	emit("paste");
}

onMounted(() => {
	loadProcessOperations();
	checkClipboard();
	document.addEventListener("mousedown", onClickOutside);
	// Search input focus
	setTimeout(() => searchInputRef.value?.focus(), 100);
});

onUnmounted(() => {
	document.removeEventListener("mousedown", onClickOutside);
});
</script>

<template>
	<div
		ref="popoverRef"
		class="action-popover"
		:style="{
			left: position.x + 'px',
			top: position.y + 'px',
		}"
		@keydown="onKeydown"
	>
		<div class="popover-header">
			<i class="fa fa-plus-circle"></i>
			<span>{{ __("Add Action") }}</span>
		</div>
		<div class="popover-search">
			<i class="fa fa-search"></i>
			<input
				ref="searchInputRef"
				type="text"
				v-model="searchQuery"
				:placeholder="__('Search actions or type Action: operation')"
				class="form-control"
			/>
		</div>
		<div class="popover-body" @wheel.stop>
			<!-- Paste Option -->
			<div
				v-if="canPaste"
				class="result-item is-option paste-option"
				@mousedown.prevent="onPasteClick"
			>
				<div class="item-icon" style="color: var(--blue-500, #3b82f6)">
					<i class="fa fa-paste"></i>
				</div>
				<div class="item-content">
					<div class="item-label">{{ __("Paste Action") }}</div>
					<div class="item-desc">{{ __("Insert from clipboard") }}</div>
				</div>
			</div>

			<div v-if="!filteredResults.length && !canPaste" class="no-results">
				{{ __("No matching actions found") }}
			</div>
			<div
				v-for="(item, idx) in filteredResults"
				:key="idx"
				:class="[
					'result-item',
					item.type === 'header' ? 'is-header' : 'is-option',
					{ active: idx === selectedIndex },
				]"
				@mousedown.prevent="selectItem(item)"
				@mouseover="selectedIndex = idx"
			>
				<template v-if="item.type === 'header'">
					{{ item.label }}
				</template>
				<template v-else>
					<div class="item-icon" :style="{ color: item.color }">
						<i :class="['fa', item.icon?.replace('fa ', '')]"></i>
					</div>
					<div class="item-content">
						<div class="item-label">{{ item.label }}</div>
						<div v-if="item.description" class="item-desc">{{ item.description }}</div>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<style scoped>
.action-popover {
	position: fixed;
	width: 280px;
	max-height: 400px;
	background: #fff;
	background-color: var(--fxr-surface, #ffffff);
	border: 1px solid var(--border-color, #dfe3e8);
	border-radius: 8px;
	box-shadow:
		0 10px 15px -3px rgba(0, 0, 0, 0.1),
		0 4px 6px -2px rgba(0, 0, 0, 0.05);
	z-index: 2147483647; /* Maximum possible z-index */
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.popover-header {
	padding: 10px 12px;
	background: #f8f9fa;
	border-bottom: 1px solid #f0f4f7;
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 700;
	font-size: 11px;
	color: var(--primary, #3b82f6);
}

.popover-search {
	padding: 8px;
	position: relative;
	border-bottom: 1px solid #f0f4f7;
}

.popover-search i {
	position: absolute;
	left: 16px;
	top: 50%;
	transform: translateY(-50%);
	color: #adb5bd;
	font-size: 10px;
}

.popover-search input {
	padding-left: 28px !important;
	height: 32px;
	font-size: 12px;
	border-radius: 4px;
	border: 1px solid var(--border-color, #dfe3e8);
}

.popover-body {
	flex: 1;
	overflow-y: auto;
	padding: 4px 0;
}

.result-item {
	padding: 8px 12px;
	cursor: pointer;
}

.is-header {
	font-size: 10px;
	font-weight: 700;
	color: #94a3b8;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	padding: 12px 12px 4px;
	cursor: default;
	background: #fff;
	position: sticky;
	top: 0;
	z-index: 1;
}

.is-option {
	display: flex;
	align-items: center;
	gap: 10px;
	transition: background 0.1s;
}

.is-option:hover,
.is-option.active {
	background: #f1f5f9;
}

.item-icon {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
}

.item-content {
	flex: 1;
	min-width: 0;
}

.item-label {
	font-size: 12px;
	font-weight: 500;
	color: #1e293b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.item-desc {
	font-size: 10px;
	color: #64748b;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.no-results {
	padding: 20px;
	text-align: center;
	color: #94a3b8;
	font-size: 12px;
}

.paste-option {
	border-bottom: 1px solid #f1f5f9;
	background: #f8fafc;
}

.paste-option:hover {
	background: #f1f5f9;
}

/* Custom Scrollbar */
.popover-body::-webkit-scrollbar {
	width: 6px;
}
.popover-body::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 3px;
}
</style>
