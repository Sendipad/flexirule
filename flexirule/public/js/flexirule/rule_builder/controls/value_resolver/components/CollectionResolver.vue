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
				<button
					v-if="!readOnly && !hasCondition"
					class="btn btn-xs btn-default text-primary"
					@click="enableCondition"
				>
					<i class="fa fa-plus mr-1"></i> {{ __("Add Filter") }}
				</button>
				<button
					v-if="!readOnly && hasCondition"
					class="btn btn-xs btn-default text-danger"
					@click="clearCondition"
				>
					<i class="fa fa-trash mr-1"></i> {{ __("Clear Filter") }}
				</button>
			</div>

			<div v-if="hasCondition" class="condition-builder-wrapper">
				<ConditionBuilder
					v-model="conditionModel"
					:docFields="rowFieldOptions"
					:readOnly="readOnly"
					:variableOptions="variableOptions"
					:isMandatory="false"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
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
}
</script>

<style scoped>
.condition-builder-wrapper {
	border: 1px solid var(--fxr-border, #dee2e6);
	border-radius: var(--fxr-radius-md, 6px);
	overflow: hidden;
}
</style>
