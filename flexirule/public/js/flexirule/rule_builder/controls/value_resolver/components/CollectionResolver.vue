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
			<div class="d-flex align-items-center justify-content-between">
				<label class="fxr-label-sm mb-0">{{ __("Filter Condition (Optional)") }}</label>
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

			<div v-if="hasCondition" class="condition-editor-card p-2 rounded border bg-light">
				<div
					v-for="(cond, idx) in conditionList"
					:key="idx"
					class="d-flex flex-column fxr-gap-1 mb-2"
				>
					<div class="row align-items-center g-1">
						<!-- Row Field -->
						<div class="col-5">
							<ComboBoxControl
								v-model="cond.left.ref"
								:options="rowFieldOptions"
								:read_only="readOnly"
								:df="{ label: '', placeholder: __('row.field') }"
								:hideLabel="true"
							/>
						</div>
						<!-- Operator -->
						<div class="col-3">
							<select
								v-model="cond.op"
								class="fxr-select form-control form-control-sm"
								:disabled="readOnly"
							>
								<option
									v-for="op in operatorOptions"
									:key="op.value"
									:value="op.value"
								>
									{{ op.label }}
								</option>
							</select>
						</div>
						<!-- Right Value -->
						<div class="col-4" v-if="!['is_set', 'is_not_set'].includes(cond.op)">
							<input
								type="text"
								v-model="cond.right.value"
								class="form-control form-control-sm"
								:disabled="readOnly"
								:placeholder="__('Value')"
							/>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useStore } from "../../../stores";
import { __ } from "../utils";
import ComboBoxControl from "../../ComboBoxControl.vue";
import SelectControl from "../../SelectControl.vue";

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

const operatorOptions = [
	{ value: "==", label: "==" },
	{ value: "!=", label: "!=" },
	{ value: ">", label: ">" },
	{ value: "<", label: "<" },
	{ value: ">=", label: ">=" },
	{ value: "<=", label: "<=" },
	{ value: "in", label: "in" },
	{ value: "contains", label: __("contains") },
	{ value: "is_set", label: __("is set") },
	{ value: "is_not_set", label: __("is not set") },
];

const sourceOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	const options = [];

	if (dt) {
		const fields = store.doc_meta[dt];
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

const childMeta = computed(() => {
	const source = props.modelValue.source || "";
	if (!source) return null;

	// Extract table field name e.g. 'doc.items' -> 'items'
	const cleanTable = source.replace(/^(doc|vars|old_doc)\./, "");
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return null;

	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return null;

	const tableField = fields.find(
		(f) => f.fieldtype === "Table" && (f.fieldname === cleanTable || f.fieldname === source)
	);
	if (!tableField || !tableField.options) return null;

	const childDoctype = tableField.options;
	return store.doc_meta[childDoctype] || null;
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
		}));
});

const hasCondition = computed(() => {
	const cond = props.modelValue.condition;
	if (!cond) return false;
	if (Array.isArray(cond)) return cond.length > 0;
	if (typeof cond === "object") return Boolean(cond.left || cond.op);
	return false;
});

const conditionList = computed({
	get() {
		const cond = props.modelValue.condition;
		if (!cond) return [];
		if (Array.isArray(cond)) return cond;
		if (typeof cond === "object") return [cond];
		return [];
	},
	set(val) {
		props.modelValue.condition = val && val.length > 0 ? val : null;
	},
});

function enableCondition() {
	props.modelValue.condition = [
		{
			left: { ref: "" },
			op: "==",
			right: { value: "" },
		},
	];
}

function clearCondition() {
	props.modelValue.condition = null;
}
</script>

<style scoped>
.condition-editor-card {
	background-color: var(--fxr-bg-card, #f8f9fa);
	border-color: var(--fxr-border, #dee2e6) !important;
}
</style>
