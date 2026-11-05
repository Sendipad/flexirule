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
	</div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import SelectControl from "../../controls/SelectControl.vue";
import { generateCollectionAlias } from "./canonical_condition_adapter.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	store: { type: Object, default: null },
});

const emit = defineEmits(["update:node", "change", "child-fields-loaded"]);

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

	// Deterministic alias generation (hidden from UI)
	const tableFieldname = segments.length ? segments[segments.length - 1] : "items";
	props.node.alias = generateCollectionAlias(tableFieldname);

	resolveAndPropagateChildFields();
	emit("change", props.node);
}

async function resolveAndPropagateChildFields() {
	const selected = tableFieldOptions.value.find((f) => f.value === props.node.collection);
	if (!selected || !selected.options) return;

	const childDocType = selected.options;
	props.node.childDocType = childDocType;

	let childFields = [];
	try {
		if (typeof frappe !== "undefined" && frappe.call) {
			const res = await frappe.call({
				method: "flexirule.ruleflow.api.get_doctype_fields",
				args: { doctype: childDocType },
			});
			const data = res.message || res;
			childFields = (data.parent_fields || []).map((f) => ({
				...f,
				value: `${props.node.alias}.${f.value}`,
				label: `${f.label} (${props.node.alias})`,
				scope: props.node.alias,
				doctype: childDocType,
			}));
		}
	} catch (e) {
		console.warn("Failed to fetch child doctype fields:", e);
	}

	emit("child-fields-loaded", {
		collectionId: props.node.id,
		childDocType,
		childFields,
		alias: props.node.alias,
	});
}

onMounted(() => {
	if (props.node.collection) {
		if (!props.node.alias || props.node.alias === "row") {
			const parts = props.node.collection.split(".").filter(Boolean);
			const tableFieldname = parts.length ? parts[parts.length - 1] : "items";
			props.node.alias = generateCollectionAlias(tableFieldname);
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
