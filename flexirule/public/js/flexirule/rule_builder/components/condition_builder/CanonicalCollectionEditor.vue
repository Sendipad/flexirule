<template>
	<div class="canonical-collection-header">
		<!-- Match quantifier -->
		<div class="col-item match-col">
			<label class="fxr-label">{{ __("Match") }}</label>
			<SelectControl
				class="fxr-select"
				:df="{
					fieldtype: 'Select',
					options: [
						{ label: __('Any'), value: 'any' },
						{ label: __('All'), value: 'all' },
						{ label: __('None'), value: 'none' },
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

		<!-- Row Alias -->
		<div class="col-item alias-col">
			<label class="fxr-label">{{ __("Alias") }}</label>
			<input
				type="text"
				v-model="node.alias"
				class="fxr-input form-control"
				placeholder="row"
				:disabled="readOnly"
				@input="onAliasChange"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import SelectControl from "../../controls/SelectControl.vue";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:node", "change"]);

const tableFieldOptions = computed(() => {
	const fields = props.docFields || [];
	return fields
		.filter((f) => f.fieldtype === "Table" || f.fieldtype === "Table MultiSelect")
		.map((f) => ({
			label: f.label || f.fieldname,
			value: f.value || `doc.${f.fieldname}`,
		}));
});

function updateQuantifier(val) {
	props.node.quantifier = val;
	emit("change", props.node);
}

function updateCollectionPath(path) {
	props.node.collection = path;
	const parts = (path || "").split(".").filter(Boolean);
	const scope = parts.length > 1 ? parts[0] : "doc";
	const segments = parts.length > 1 ? parts.slice(1) : parts.length === 1 ? [parts[0]] : [];
	props.node.source = { scope, segments };

	if (!props.node.alias && segments.length) {
		props.node.alias = segments[segments.length - 1].replace(/[^a-zA-Z0-9_]/g, "_");
	}
	emit("change", props.node);
}

function onAliasChange() {
	emit("change", props.node);
}
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
	width: 100px;
}
.alias-col {
	width: 120px;
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
	.alias-col {
		width: 100%;
	}
}
</style>
