<template>
	<!-- Step 1: Source DocType -->
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("1. Source DocType") }}</label>
		<ComboBoxControl
			v-model="modelValue.linked_doctype"
			doctype="DocType"
			:read_only="readOnly"
			:placeholder="__('Select Source DocType...')"
			hide-label
			allow-custom-value
		/>
	</div>

	<!-- Step 2: Source Document -->
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("2. Source Document") }}</label>
		<div class="d-flex fxr-gap-2">
			<select
				class="fxr-select"
				style="width: 100px"
				v-model="modelValue.link_source_type"
				:disabled="readOnly"
				@change="modelValue.link_field = ''"
			>
				<option value="doc_field">{{ __("Field") }}</option>
				<option value="variable">{{ __("Var") }}</option>
				<option value="expression">{{ __("Expr") }}</option>
			</select>
			<ComboBoxControl
				v-if="modelValue.link_source_type !== 'expression'"
				class="flex-1 min-w-0"
				v-model="modelValue.link_field"
				:options="sourceLinkOptions"
				:read_only="readOnly"
				:placeholder="
					modelValue.link_source_type === 'variable'
						? __('Search variable...')
						: __('Select field...')
				"
				:allow-custom-value="modelValue.link_source_type === 'variable'"
				hide-label
			/>
			<input
				v-else
				type="text"
				class="fxr-input flex-1"
				v-model="modelValue.link_field"
				:disabled="readOnly"
				:placeholder="__('e.g. doc.party')"
			/>
		</div>
	</div>

	<!-- Step 3: Fetch Field -->
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("3. Fetch Field") }}</label>
		<ComboBoxControl
			v-model="modelValue.fetch_field"
			:options="fetchFieldOptions"
			:read_only="readOnly || !modelValue.linked_doctype"
			:loading="fetchMetaLoading"
			:placeholder="fetchMetaLoading ? __('Loading...') : __('Select field to fetch...')"
			:allow-custom-value="true"
			hide-label
		/>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useStore } from "../../../stores";
import ComboBoxControl from "../../ComboBoxControl.vue";
import { __ } from "../utils";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
	variableOptions: {
		type: Array,
		default: () => [],
	},
	context: Object,
});

const store = useStore();
const fetchMetaLoading = ref(false);

const resolverFieldname = computed(() => {
	const fieldname =
		props.context?.fieldname ||
		props.context?.target ||
		props.context?.df?.fieldname ||
		props.context?.df?.value ||
		"value_resolver";
	return String(fieldname)
		.replace(/^doc\./, "")
		.replace(/^vars\./, "");
});

const prioritizedFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];

	const prioritizedTypes = ["Link", "Dynamic Link", "Data", "Select"];

	return [...fields]
		.sort((a, b) => {
			const aPrio = prioritizedTypes.indexOf(a.fieldtype);
			const bPrio = prioritizedTypes.indexOf(b.fieldtype);

			if (aPrio !== -1 && bPrio !== -1) return aPrio - bPrio;
			if (aPrio !== -1) return -1;
			if (bPrio !== -1) return 1;
			return 0;
		})
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
			options: f.options,
			fieldtype: f.fieldtype,
			icon: ["Link", "Dynamic Link"].includes(f.fieldtype) ? "fa fa-link" : "fa fa-columns",
		}));
});

const sourceLinkOptions = computed(() => {
	if (props.modelValue.link_source_type === "variable") {
		const vars = props.variableOptions || [];
		return vars.map((v) => ({
			label: `${v.label || v.value} (vars.${v.value})`,
			value: `vars.${v.value}`,
			options: v.options,
			fieldtype: v.fieldtype,
		}));
	}
	return prioritizedFieldOptions.value;
});

const fetchFieldOptions = computed(() => {
	const linkedDt = props.modelValue.linked_doctype;
	if (!linkedDt) return [];
	return store.get_fields_for_doctype(linkedDt, { valueMode: "fieldname" });
});

watch(
	() => props.modelValue.link_field,
	async (newVal) => {
		if (!newVal) return;

		const opt = sourceLinkOptions.value.find((o) => o.value === newVal);
		if (opt && (opt.options || opt.fieldtype === "Dynamic Link")) {
			let linkedDt = opt.options;
			if (opt.fieldtype === "Dynamic Link") {
				linkedDt = `doc.${opt.options}`;
			}

			if (linkedDt && !props.modelValue.linked_doctype) {
				props.modelValue.linked_doctype = linkedDt;
			}
		}
	}
);

watch(
	() => props.modelValue.linked_doctype,
	async (newVal, oldVal) => {
		if (!newVal) {
			props.modelValue.fetch_field = "";
			return;
		}

		if (newVal !== oldVal) {
			if (!props.modelValue.fetch_field && resolverFieldname.value) {
				props.modelValue.fetch_field = resolverFieldname.value;
			}
		}

		if (newVal && !newVal.startsWith("doc.") && !newVal.startsWith("vars.")) {
			fetchMetaLoading.value = true;
			try {
				await store.fetch_metadata(newVal);
			} finally {
				fetchMetaLoading.value = false;
			}
		}
	}
);
</script>
