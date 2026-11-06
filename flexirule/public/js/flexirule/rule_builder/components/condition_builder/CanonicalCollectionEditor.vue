<template>
	<div class="canonical-collection-header">
		<!-- Match quantifier (Collection-level: Any / All / None) -->
		<div class="col-item match-col">
			<label class="fxr-label">{{ __("Check table") }}</label>
			<SelectControl
				class="fxr-select"
				:df="{
					fieldtype: 'Select',
					options: [
						{ label: __('At least one row'), value: 'any' },
						{ label: __('Every row'), value: 'all' },
						{ label: __('No rows'), value: 'none' },
					],
					reqd: 1,
				}"
				:modelValue="node.quantifier"
				:read_only="readOnly"
				:hideLabel="true"
				@update:modelValue="updateQuantifier"
			/>
		</div>

		<!-- Table field selector -->
		<div class="col-item table-col flex-grow-1">
			<label class="fxr-label">{{ __("Table Field") }}</label>
			<SelectControl
				class="fxr-select"
				:df="{
					fieldtype: 'Select',
					options: tableFieldOptions,
					reqd: 1,
				}"
				:modelValue="node.collection"
				:read_only="readOnly"
				:hideLabel="true"
				@update:modelValue="updateCollectionPath"
			/>
		</div>

		<!-- Row-level condition quantifier (when multiple child conditions exist) -->
		<div v-if="hasMultipleChildConditions" class="col-item row-quantifier-col">
			<label class="fxr-label">{{ __("Row condition logic") }}</label>
			<SelectControl
				class="fxr-select"
				:df="{
					fieldtype: 'Select',
					options: [
						{ label: __('Match all conditions'), value: 'and' },
						{ label: __('Match any condition'), value: 'or' },
					],
					reqd: 1,
				}"
				:modelValue="node.rowQuantifier || 'and'"
				:read_only="readOnly"
				:hideLabel="true"
				@update:modelValue="updateRowQuantifier"
			/>
		</div>

		<!-- Metadata Loading & Error Status -->
		<div
			v-if="metaStatus === 'loading'"
			class="col-12 py-1 px-2 small text-muted d-flex align-items-center"
		>
			<i class="fa fa-spinner fa-spin mr-2"></i>
			<span>{{ __("Loading child table fields...") }}</span>
		</div>
		<div
			v-else-if="metaStatus === 'failed'"
			class="col-12 py-1 px-2 small alert alert-danger d-flex align-items-center justify-content-between mb-0"
		>
			<span>{{ __("Could not load child fields: ") }}{{ metaError }}</span>
			<button
				type="button"
				class="btn btn-xs btn-outline-danger"
				@click="resolveAndPropagateChildFields"
			>
				{{ __("Retry") }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import SelectControl from "../../controls/SelectControl.vue";
import { generateCollectionAlias } from "./canonical_condition_adapter.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	ancestorAliases: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	store: { type: Object, default: null },
});

const emit = defineEmits(["update:node", "change", "child-fields-loaded"]);

const metaStatus = ref("idle"); // 'idle' | 'loading' | 'loaded' | 'failed'
const metaError = ref(null);
let activeRequestId = 0;

const hasMultipleChildConditions = computed(() => {
	const ch = props.node.children;
	return Array.isArray(ch) && ch.length > 1;
});

const tableFieldOptions = computed(() => {
	const fields = props.docFields || [];
	return fields
		.filter((f) => f.fieldtype === "Table" || f.fieldtype === "Table MultiSelect")
		.map((f) => ({
			label: f.label || f.fieldname,
			value: f.value || `doc.${f.fieldname}`,
			options: f.options,
			fieldname: f.fieldname,
		}));
});

function updateQuantifier(val) {
	props.node.quantifier = val;
	emit("change", props.node);
}

function updateRowQuantifier(val) {
	props.node.rowQuantifier = val;
	emit("change", props.node);
}

function updateCollectionPath(path) {
	props.node.collection = path;
	const parts = (path || "").split(".").filter(Boolean);
	const scope = parts.length > 1 ? parts[0] : "doc";
	const segments = parts.length > 1 ? parts.slice(1) : parts.length === 1 ? [parts[0]] : [];
	props.node.source = { scope, segments };

	// Deterministic alias generation with ancestor alias awareness (hidden from UI)
	const tableFieldname = segments.length ? segments[segments.length - 1] : "items";
	const existingAliases = new Set(props.ancestorAliases || []);
	props.node.alias = generateCollectionAlias(tableFieldname, existingAliases);

	resolveAndPropagateChildFields();
	emit("change", props.node);
}

async function resolveAndPropagateChildFields() {
	const currentRequestId = ++activeRequestId;
	const selected = tableFieldOptions.value.find((f) => f.value === props.node.collection);
	if (!selected || !selected.options) {
		metaStatus.value = "idle";
		metaError.value = null;
		return;
	}

	// Capture snapshot of request identity before awaiting async calls
	const capturedCollection = props.node.collection;
	const capturedChildDocType = selected.options;
	const capturedAlias = props.node.alias;

	props.node.childDocType = capturedChildDocType;
	metaStatus.value = "loading";
	metaError.value = null;

	let childFields = [];
	try {
		if (typeof frappe !== "undefined" && frappe.call) {
			const res = await frappe.call({
				method: "flexirule.ruleflow.api.get_doctype_fields",
				args: { doctype: capturedChildDocType },
			});

			// Stale response protection: if selection or alias changed in flight, discard response
			if (
				currentRequestId !== activeRequestId ||
				props.node.collection !== capturedCollection ||
				props.node.alias !== capturedAlias
			) {
				return;
			}

			const data = res.message || res;
			childFields = (data.parent_fields || []).map((f) => ({
				...f,
				value: `${capturedAlias}.${f.value}`,
				label: `${f.label} (${capturedAlias})`,
				scope: capturedAlias,
				doctype: capturedChildDocType,
			}));
			metaStatus.value = "loaded";
		} else {
			if (
				currentRequestId !== activeRequestId ||
				props.node.collection !== capturedCollection ||
				props.node.alias !== capturedAlias
			) {
				return;
			}
			metaStatus.value = "loaded";
		}

		emit("child-fields-loaded", {
			collectionId: props.node.id,
			childDocType: capturedChildDocType,
			childFields,
			alias: capturedAlias,
			status: metaStatus.value,
		});
	} catch (e) {
		if (
			currentRequestId !== activeRequestId ||
			props.node.collection !== capturedCollection ||
			props.node.alias !== capturedAlias
		) {
			return;
		}
		const msg = e?.message || "Failed to fetch child doctype fields";
		metaStatus.value = "failed";
		metaError.value = msg;
		emit("child-fields-loaded", {
			collectionId: props.node.id,
			childDocType: capturedChildDocType,
			childFields: [],
			alias: capturedAlias,
			status: "failed",
			error: msg,
		});
	}
}

onMounted(() => {
	if (props.node.collection) {
		const existingAliases = new Set(props.ancestorAliases || []);
		if (
			!props.node.alias ||
			props.node.alias === "row" ||
			existingAliases.has(props.node.alias)
		) {
			const parts = props.node.collection.split(".").filter(Boolean);
			const tableFieldname = parts.length ? parts[parts.length - 1] : "items";
			props.node.alias = generateCollectionAlias(tableFieldname, existingAliases);
		}
		resolveAndPropagateChildFields();
	}
});
</script>

<style scoped>
.canonical-collection-header {
	display: flex;
	gap: var(--fxr-space-3, 12px);
	align-items: flex-end;
	flex-wrap: wrap;
	width: 100%;
}
.col-item {
	display: flex;
	flex-direction: column;
	min-width: 0;
}
.match-col {
	width: 160px;
}
.row-quantifier-col {
	width: 180px;
}
.fxr-label {
	font-size: var(--fxr-text-xs, 11px);
	font-weight: var(--fxr-weight-semibold, 600);
	color: var(--fxr-text-secondary, #6b7280);
	margin-bottom: 2px;
}
@media (max-width: 768px) {
	.canonical-collection-header {
		flex-direction: column;
		align-items: stretch;
	}
	.match-col,
	.row-quantifier-col {
		width: 100%;
	}
}
</style>
