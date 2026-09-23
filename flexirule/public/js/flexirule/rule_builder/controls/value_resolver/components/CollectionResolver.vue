<template>
	<div class="collection-resolver d-flex flex-column fxr-gap-2">
		<!-- Source Collection -->
		<div class="d-flex flex-column fxr-gap-1">
			<ComboBoxControl
				v-model="modelValue.source"
				:options="sourceOptions"
				:read_only="readOnly"
				:df="{
					label: __('Collection Source'),
					placeholder: __('e.g. doc.items or vars.list'),
				}"
			/>
		</div>

		<!-- Operation -->
		<div class="d-flex flex-column fxr-gap-1">
			<SelectControl
				v-model="modelValue.operation"
				:options="operationOptions"
				:read_only="readOnly"
				:df="{ label: __('Operation') }"
			/>
		</div>

		<!-- Target Field (for pluck and unique) -->
		<div
			v-if="['pluck', 'unique'].includes(modelValue.operation)"
			class="d-flex flex-column fxr-gap-1"
		>
			<ComboBoxControl
				v-model="modelValue.target_field"
				:options="targetFieldOptions"
				:read_only="readOnly"
				:df="{ label: __('Target Field'), placeholder: __('e.g. item_code or rate') }"
			/>
		</div>

		<!-- Filter Condition Section -->
		<div class="d-flex flex-column fxr-gap-1 mt-1">
			<div class="d-flex align-items-center justify-content-between mb-1">
				<label class="fxr-label-sm mb-0">{{ __("FILTER CONDITION (OPTIONAL)") }}</label>
			</div>

			<button
				type="button"
				class="fxr-btn fxr-btn--sm w-100 when-toggle-btn"
				:class="{
					'is-active': hasCondition,
					'is-default': !hasCondition,
				}"
				:disabled="readOnly"
				@click="openConditionModal"
			>
				<i
					:class="hasCondition ? 'fa fa-filter text-primary' : 'fa fa-plus-circle'"
					class="mr-2"
				></i>
				<span class="truncate">
					{{ hasCondition ? __("Condition Set") : __("Add Filter Condition") }}
				</span>
			</button>
		</div>

		<Teleport to="body">
			<div
				v-if="conditionModalOpen"
				class="fxr-modal-overlay"
				@click.self="closeConditionModal"
			>
				<div class="fxr-modal-card">
					<div class="d-flex align-items-center justify-content-between mb-2">
						<h5 class="mb-0">{{ __("Collection Filter Condition") }}</h5>
						<button
							type="button"
							class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost"
							@click="closeConditionModal"
						>
							<i class="fa fa-times"></i>
						</button>
					</div>
					<div class="condition-builder-wrap">
						<ConditionBuilder
							v-model="conditionModel"
							:docFields="rowFieldOptions"
							:readOnly="readOnly"
							:variableOptions="variableOptions"
							:isMandatory="false"
						/>
					</div>
					<div class="d-flex justify-content-between mt-3">
						<button
							type="button"
							class="fxr-btn fxr-btn--sm fxr-btn--ghost text-danger"
							@click="clearCondition"
						>
							{{ __("Clear Condition") }}
						</button>
						<button
							type="button"
							class="fxr-btn fxr-btn--sm fxr-btn--primary"
							@click="closeConditionModal"
						>
							{{ __("Done") }}
						</button>
					</div>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useStore } from "../../../stores";
import { useMetaStore } from "../../../stores/useMetaStore";
import { __ } from "../utils";
import ComboBoxControl from "../../ComboBoxControl.vue";
import SelectControl from "../../SelectControl.vue";
import ConditionBuilder from "../../../components/condition_builder/ConditionBuilder.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			source: "",
			operation: "any",
			target_field: "",
			condition: null,
		}),
	},
	doctype: {
		type: String,
		default: "",
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
	context: {
		type: Object,
		default: () => ({}),
	},
	variableOptions: {
		type: Array,
		default: () => [],
	},
});

const store = useStore();
const metaStore = useMetaStore();
const conditionModalOpen = ref(false);

const operationOptions = [
	{ value: "count", label: __("Count Rows (count)") },
	{ value: "any", label: __("Check Any Match (any)") },
	{ value: "all", label: __("Check All Match (all)") },
	{ value: "first", label: __("Find First Row (first)") },
	{ value: "find", label: __("Find Row (find)") },
	{ value: "filter", label: __("Filter Sub-Collection (filter)") },
	{ value: "pluck", label: __("Extract Field Values (pluck)") },
	{ value: "unique", label: __("Extract Unique Values (unique)") },
];

const sourceOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	const options = [];

	if (dt) {
		const fields = metaStore.doc_meta[dt] || store.doc_meta[dt];
		if (fields && Array.isArray(fields)) {
			fields
				.filter((f) => f.fieldtype === "Table")
				.forEach((f) => {
					options.push({
						label: `doc.${f.fieldname} (${f.label || f.fieldname})`,
						value: `doc.${f.fieldname}`,
					});
				});
		}
	}

	if (props.variableOptions && Array.isArray(props.variableOptions)) {
		props.variableOptions.forEach((v) => {
			const val = typeof v === "string" ? v : v.value || v.label;
			const cleanVal = String(val).startsWith("vars.") ? val : `vars.${val}`;
			if (!options.some((o) => o.value === cleanVal)) {
				options.push({
					label: cleanVal,
					value: cleanVal,
				});
			}
		});
	}

	return options;
});

watch(
	() => [props.modelValue.source, props.doctype, store.rule_doc?.document_type],
	async ([newSource]) => {
		const dt = store.rule_doc?.document_type || props.doctype;
		if (dt && !metaStore.doc_meta[dt]) {
			await metaStore.fetch_metadata(dt);
		}
		if (!newSource) return;

		const cleanTable = String(newSource).replace(/^(doc|vars|old_doc)\./, "");
		const fields = metaStore.doc_meta[dt] || store.doc_meta[dt];
		if (!fields || !Array.isArray(fields)) return;

		const tableField = fields.find(
			(f) =>
				f.fieldtype === "Table" && (f.fieldname === cleanTable || f.fieldname === newSource)
		);
		if (tableField && tableField.options && !metaStore.doc_meta[tableField.options]) {
			await metaStore.fetch_metadata(tableField.options);
		}
	},
	{ immediate: true }
);

const childMeta = computed(() => {
	const source = props.modelValue.source || "";
	if (!source) return null;

	const cleanTable = source.replace(/^(doc|vars|old_doc)\./, "");
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return null;

	const fields = metaStore.doc_meta[dt] || store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return null;

	const tableField = fields.find(
		(f) => f.fieldtype === "Table" && (f.fieldname === cleanTable || f.fieldname === source)
	);
	if (!tableField || !tableField.options) return null;

	const childDoctype = tableField.options;
	return metaStore.doc_meta[childDoctype] || store.doc_meta[childDoctype] || null;
});

const targetFieldOptions = computed(() => {
	if (!childMeta.value || !Array.isArray(childMeta.value)) return [];
	return childMeta.value
		.filter((f) => !["Section Break", "Column Break", "Tab Break"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});

const rowFieldOptions = computed(() => {
	if (!childMeta.value || !Array.isArray(childMeta.value)) return [];
	return childMeta.value
		.filter((f) => !["Section Break", "Column Break", "Tab Break"].includes(f.fieldtype))
		.map((f) => ({
			label: `row.${f.fieldname} (${f.label || f.fieldname})`,
			value: `row.${f.fieldname}`,
			fieldname: f.fieldname,
			fieldtype: f.fieldtype,
		}));
});

const hasCondition = computed(() => {
	const cond = props.modelValue.condition;
	if (!cond) return false;
	if (Array.isArray(cond)) return cond.length > 0;
	if (typeof cond === "object") return Boolean(cond.conditions?.length || cond.left || cond.op);
	return false;
});

const conditionModel = computed({
	get() {
		const cond = props.modelValue.condition;
		if (!cond) return { op: "and", conditions: [] };
		if (typeof cond === "object" && !Array.isArray(cond) && cond.conditions) {
			return cond;
		}
		if (Array.isArray(cond)) {
			return { op: "and", conditions: cond };
		}
		if (typeof cond === "object") {
			return { op: "and", conditions: [cond] };
		}
		return { op: "and", conditions: [] };
	},
	set(val) {
		props.modelValue.condition = val && val.conditions?.length > 0 ? val : null;
	},
});

function openConditionModal() {
	if (props.readOnly) return;
	if (!hasCondition.value) {
		enableCondition();
	}
	conditionModalOpen.value = true;
}

function closeConditionModal() {
	conditionModalOpen.value = false;
}

function enableCondition() {
	const defaultRef = rowFieldOptions.value[0]?.value || "row.";
	props.modelValue.condition = {
		op: "and",
		conditions: [
			{
				left: { ref: defaultRef },
				op: "==",
				right: { value: "" },
			},
		],
	};
}

function clearCondition() {
	props.modelValue.condition = null;
	conditionModalOpen.value = false;
}
</script>

<style scoped>
.when-toggle-btn {
	display: flex;
	align-items: center;
	justify-content: flex-start;
	padding: 6px 12px;
	font-weight: 600;
	font-size: 12px;
	border-radius: var(--fxr-radius-md, 6px);
	border: 1px solid var(--fxr-border, #dee2e6);
	background-color: var(--fxr-bg-card, #ffffff);
	cursor: pointer;
	transition: all 0.2s ease;
}

.when-toggle-btn:hover:not(:disabled) {
	border-color: var(--fxr-accent, #3b82f6);
	background-color: var(--fxr-bg-hover, #f1f5f9);
}

.when-toggle-btn.is-active {
	background-color: color-mix(in srgb, var(--fxr-accent, #3b82f6) 12%, transparent);
	color: var(--fxr-accent, #3b82f6);
	border-color: var(--fxr-accent, #3b82f6);
}

.fxr-modal-overlay {
	position: fixed;
	inset: 0;
	background-color: rgba(0, 0, 0, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 25000;
}

.fxr-modal-card {
	width: min(880px, 92vw);
	max-height: 86vh;
	background-color: var(--fxr-surface-elevated, #ffffff);
	border-radius: 14px;
	border: 1px solid var(--fxr-border-subtle, #dee2e6);
	padding: 16px;
	overflow: hidden;
	display: flex;
	flex-direction: column;
	box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
}

.condition-builder-wrap {
	overflow: auto;
	border: 1px solid var(--fxr-border-subtle, #dee2e6);
	border-radius: 12px;
	padding: 10px;
	background-color: var(--fxr-surface-soft, #f8f9fa);
}
</style>
