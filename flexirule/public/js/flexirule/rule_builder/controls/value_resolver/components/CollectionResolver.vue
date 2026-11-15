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

		<!-- Target Field (for sum, avg, pluck, and unique) -->
		<div
			v-if="['sum', 'avg', 'pluck', 'unique'].includes(modelValue.operation)"
			class="d-flex flex-column fxr-gap-1"
		>
			<ComboBoxControl
				v-model="modelValue.target_field"
				:options="targetFieldOptions"
				:read_only="readOnly"
				:df="{ label: __('Target Field'), placeholder: __('e.g. amount or rate') }"
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
				v-show="conditionModalOpen"
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
						<CanonicalConditionBuilder
							ref="conditionBuilderRef"
							v-model="conditionModel"
							:docFields="rowFieldOptions"
							:readOnly="readOnly"
							:variableOptions="variableOptions"
							:currentDocType="parentDocType"
							:collectionSource="modelValue.source"
							:store="ruleStore"
							:isMandatory="false"
							:showValidation="conditionShowValidation"
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
import { useMetaStore, useRuleStore } from "../../../stores";
import { __ } from "../utils";
import ComboBoxControl from "../../ComboBoxControl.vue";
import SelectControl from "../../SelectControl.vue";
import CanonicalConditionBuilder from "../../../components/condition_builder/CanonicalConditionBuilder.vue";

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

const metaStore = useMetaStore();
const ruleStore = useRuleStore();
const parentDocType = computed(() => ruleStore.rule_doc?.document_type || props.doctype || "");
const conditionModalOpen = ref(false);
const conditionBuilderRef = ref(null);
const conditionShowValidation = ref(false);

const operationOptions = [
	{ value: "sum", label: __("Sum Numeric Values (sum)") },
	{ value: "avg", label: __("Average Numeric Values (avg)") },
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
	const dt = parentDocType.value;
	const options = [];

	if (dt) {
		const fields = metaStore.doc_meta[dt];
		if (fields && Array.isArray(fields)) {
			fields
				.filter((f) => ["Table", "Table MultiSelect"].includes(f.fieldtype))
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
	() => [props.modelValue.source, props.doctype, ruleStore.rule_doc?.document_type],
	async ([newSource]) => {
		const dt = parentDocType.value;
		if (dt && !metaStore.doc_meta[dt]) {
			await metaStore.fetch_metadata(dt);
		}
		if (!newSource) return;

		const cleanTable = String(newSource).replace(/^(doc|vars|old_doc)\./, "");
		const fields = metaStore.doc_meta[dt];
		if (!fields || !Array.isArray(fields)) return;

		const tableField = fields.find(
			(f) =>
				["Table", "Table MultiSelect"].includes(f.fieldtype) &&
				(f.fieldname === cleanTable || f.fieldname === newSource)
		);
		if (tableField && tableField.options && !metaStore.doc_meta[tableField.options]) {
			await metaStore.fetch_metadata(tableField.options);
		}
	},
	{ immediate: true }
);

const rowDocType = computed(() => {
	const source = String(props.modelValue.source || "").trim();
	if (!source) return "";

	const parts = source.split(".").filter(Boolean);
	const scope = parts.length > 1 ? parts[0] : "doc";
	const segments = parts.length > 1 ? parts.slice(1) : parts;
	if (scope !== "doc" || segments.length !== 1) return "";

	const parentDoctype = parentDocType.value;
	if (!parentDoctype) return "";

	const fields = metaStore.doc_meta[parentDoctype];
	if (!Array.isArray(fields)) return "";

	const tableField = fields.find(
		(field) =>
			["Table", "Table MultiSelect"].includes(field.fieldtype) &&
			field.fieldname === segments[0]
	);
	return tableField?.options || "";
});

const childMeta = computed(() => {
	if (!rowDocType.value) return null;
	return metaStore.doc_meta[rowDocType.value] || null;
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
			options: f.options || "",
			doctype: rowDocType.value,
		}));
});

const hasCondition = computed(() => {
	const cond = props.modelValue.condition;
	if (!cond) return false;
	if (Array.isArray(cond)) return cond.length > 0;
	if (cond.type === "group") return Boolean(cond.children?.length);
	if (cond.type === "comparison" || cond.type === "collection_predicate") return true;
	if (typeof cond === "object") return Boolean(cond.conditions?.length || cond.left || cond.op);
	return false;
});

const conditionModel = computed({
	get() {
		return props.modelValue.condition || null;
	},
	set(value) {
		props.modelValue.condition = value || null;
	},
});

watch(
	conditionModel,
	() => {
		conditionShowValidation.value = false;
	},
	{ deep: true }
);

function openConditionModal() {
	if (props.readOnly) return;
	conditionModalOpen.value = true;
}

function closeConditionModal() {
	conditionModalOpen.value = false;
}

function clearCondition() {
	props.modelValue.condition = null;
	conditionShowValidation.value = false;
	conditionModalOpen.value = false;
}

async function validate() {
	const builderTree = conditionBuilderRef.value?.getTree?.();
	const hasDraftNodes = Array.isArray(builderTree?.children) && builderTree.children.length > 0;
	if (!conditionModel.value && !hasDraftNodes) {
		return { valid: true, errors: [] };
	}
	conditionShowValidation.value = true;
	if (conditionBuilderRef.value?.validate) {
		return await conditionBuilderRef.value.validate();
	}
	return {
		valid: false,
		errors: [__("Collection filter condition editor is unavailable")],
	};
}

defineExpose({ validate });
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
	z-index: 20000;
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
