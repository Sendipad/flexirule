<template>
	<div class="subrule-node-config" ref="containerRef">
		<div class="form-group relative" v-fxr-fieldname="'rule'">
			<div class="d-flex justify-content-between align-items-center mb-1">
				<label class="mb-0">{{ __("Select Rule") }}</label>
				<div class="custom-control custom-switch custom-switch-sm">
					<input
						type="checkbox"
						class="custom-control-input"
						id="filterCompatible"
						v-model="onlyCompatible"
					/>
					<label class="custom-control-label small" for="filterCompatible">{{
						__("Only Compatible")
					}}</label>
				</div>
			</div>
			<div class="input-group">
				<input
					type="text"
					class="form-control"
					v-model="subRuleSearch"
					@focus="showSuggestions = true"
					:placeholder="__('Search rule...')"
				/>
				<div class="input-group-append" v-if="nodeData?.rule">
					<button
						class="btn btn-outline-secondary btn-xs"
						type="button"
						@click="clearRule"
					>
						<i class="fa fa-times"></i>
					</button>
				</div>
			</div>

			<div v-if="showSuggestions" class="suggestions-dropdown">
				<div
					v-for="r in filteredRules"
					:key="r.name"
					class="suggestion-item"
					:class="{
						'incompatible-item': r.document_type && r.document_type !== parentDocType,
					}"
					@click="selectRule(r)"
				>
					<div class="d-flex justify-content-between align-items-center w-100">
						<div class="suggestion-name">
							{{ r.rule_name || r.name }}
							<span
								v-if="r.document_type === parentDocType"
								class="text-success ml-1"
								style="font-size: 10px"
							>
								<i class="fa fa-check-circle"></i>
							</span>
						</div>
						<span
							v-if="r.trigger_event === 'Manual'"
							class="badge badge-info"
							style="font-size: 9px"
							>{{ __("Manual") }}</span
						>
						<span v-else class="badge border text-muted" style="font-size: 9px">{{
							r.trigger_event
						}}</span>
					</div>
					<div
						class="suggestion-path d-flex justify-content-between"
						style="font-size: 10px"
					>
						<span>{{ r.name }}</span>
						<span v-if="r.document_type" class="text-muted italic">{{
							r.document_type
						}}</span>
						<span v-else class="text-primary italic">{{ __("Global") }}</span>
					</div>
				</div>
				<div v-if="!filteredRules.length" class="p-2 text-muted">
					{{ __("No rules found") }}
				</div>
			</div>

			<div v-if="selectedRuleMetadata" class="mt-2 compatibility-badge-container">
				<div
					v-if="!compatibilityStatus.ok"
					class="alert alert-warning p-2 mb-0"
					style="font-size: 11px"
				>
					<i class="fa fa-exclamation-triangle"></i> {{ compatibilityStatus.message }}
				</div>
				<div
					v-else-if="compatibilityStatus.message"
					class="text-muted p-1"
					style="font-size: 10px"
				>
					<i class="fa fa-info-circle"></i> {{ compatibilityStatus.message }}
				</div>
			</div>

			<div class="help-text text-muted" style="font-size: 11px">
				{{ __("Rule to execute. Context vars are shared.") }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";
import { useStore } from "../../stores";

const props = defineProps({
	nodeData: Object,
	availableRules: { type: Array, default: () => [] },
});

const emit = defineEmits(["update-field"]);
const store = useStore();

const subRuleSearch = ref("");
const showSuggestions = ref(false);
const onlyCompatible = ref(true);

const parentDocType = computed(() => {
	// Traverse parent if necessary? Usually rule_doc in store is sufficient
	return store.rule_doc?.document_type;
});

const filteredRules = computed(() => {
	const search = subRuleSearch.value.toLowerCase();
	const rules = props.availableRules || [];

	return rules
		.filter((r) => {
			const matchesSearch =
				r.name.toLowerCase().includes(search) ||
				(r.rule_name && r.rule_name.toLowerCase().includes(search));

			if (!matchesSearch) return false;

			if (onlyCompatible.value) {
				const isCompatible = !r.document_type || r.document_type === parentDocType.value;
				return isCompatible;
			}
			return true;
		})
		.sort((a, b) => {
			// Priority 1: DocType Match
			const aMatch = a.document_type === parentDocType.value;
			const bMatch = b.document_type === parentDocType.value;
			if (aMatch && !bMatch) return -1;
			if (!aMatch && bMatch) return 1;

			// Priority 2: Global (No DocType)
			const aGlobal = !a.document_type;
			const bGlobal = !b.document_type;
			if (aGlobal && !bGlobal) return -1;
			if (!aGlobal && bGlobal) return 1;

			return 0;
		});
});

const selectedRuleMetadata = computed(() => {
	return props.availableRules.find((r) => r.name === props.nodeData?.rule);
});

const compatibilityStatus = ref({ ok: true, message: "" });

watch(
	() => props.nodeData?.rule,
	async (newVal) => {
		if (newVal) {
			const r = props.availableRules.find((r) => r.name === newVal);
			subRuleSearch.value = r ? r.rule_name || r.name : newVal;
			await validateCompatibility(r);
		} else {
			subRuleSearch.value = "";
			compatibilityStatus.value = { ok: true, message: "" };
		}
	},
	{ immediate: true }
);

async function validateCompatibility(rule) {
	if (!rule) return;

	// 1. Basic DocType Check
	if (rule.document_type && rule.document_type !== parentDocType.value) {
		compatibilityStatus.value = {
			ok: false,
			message: __("DocType handles {0}, but parent rule is for {1}", [
				rule.document_type,
				parentDocType.value,
			]),
		};
		return;
	}

	// 2. Condition Validation (if exists)
	if (rule.trigger_condition || rule.compiled_expression) {
		compatibilityStatus.value = {
			ok: true,
			message: rule.trigger_condition
				? __("Target rule has conditions; ensure input mapping satisfies them.")
				: null,
		};
	} else {
		compatibilityStatus.value = { ok: true, message: "" };
	}
}

function selectRule(rule) {
	subRuleSearch.value = rule.rule_name || rule.name;
	emit("update-field", "rule", rule.name);
	showSuggestions.value = false;
	nextTick().then(() => {
		// Surgical expansion removed per user request
	});
}

function clearRule() {
	subRuleSearch.value = "";
	emit("update-field", "rule", "");
	showSuggestions.value = false;
	nextTick().then(() => {
		// Expansion removed per user request
	});
}

// Click outside handler
const containerRef = ref(null);
function handleClickOutside(e) {
	if (containerRef.value && !containerRef.value.contains(e.target)) {
		showSuggestions.value = false;
	}
}

onMounted(() => {
	document.addEventListener("mousedown", handleClickOutside);
});

onUnmounted(() => {
	document.removeEventListener("mousedown", handleClickOutside);
});
</script>

<style scoped>
.suggestions-dropdown {
	position: absolute;
	top: 100%;
	left: 0;
	right: 0;
	background-color: var(--fxr-surface-elevated);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	box-shadow: var(--fxr-shadow-md);
	max-height: 250px;
	overflow-y: auto;
	z-index: 100;
}

.suggestion-item {
	padding: 8px 12px;
	cursor: pointer;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.suggestion-item:hover {
	background-color: var(--fxr-bg-hover);
}

.incompatible-item {
	opacity: 0.7;
	background-color: var(--fxr-warning-soft);
}

.incompatible-item:hover {
	background-color: var(--fxr-bg-hover);
	opacity: 1;
}

.suggestion-name {
	font-weight: 500;
}

.suggestion-path {
	color: var(--text-muted);
}
</style>
