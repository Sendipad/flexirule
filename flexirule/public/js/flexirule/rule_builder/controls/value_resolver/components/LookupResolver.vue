<template>
	<div class="lookup-resolver-wrap">
		<!-- Step 1: Target DocType Mode & Selection -->
		<CollapsibleSection
			:label="__('1. Target DocType')"
			:initial-collapsed="!!(modelValue.target_doctype || modelValue.doctype_source)"
			:read-only="readOnly"
		>
			<template #header-actions>
				<span v-if="targetDocTypeHeader" class="fxr-text-xs text-muted truncate ml-2">
					{{ targetDocTypeHeader }}
				</span>
			</template>

			<div class="d-flex fxr-gap-2 mb-2 align-items-center">
				<label class="fxr-text-xs text-muted mb-0 mr-2">{{ __('Mode:') }}</label>
				<SelectControl
					style="width: 220px"
					v-model="modelValue.doctype_mode"
					:options="doctypeModeOptions"
					:read_only="readOnly"
					no-label
					@change="onDoctypeModeChange"
				/>
			</div>

			<!-- Fixed DocType Picker -->
			<ComboBoxControl
				v-if="modelValue.doctype_mode === 'static'"
				v-model="modelValue.target_doctype"
				doctype="DocType"
				:read_only="readOnly"
				:placeholder="__('Select Target DocType (e.g. Customer)...')"
				hide-label
				allow-custom-value
			/>

			<!-- Dynamic DocType Source Picker -->
			<ComboBoxControl
				v-else
				v-model="modelValue.doctype_source"
				:options="doctypeSourceFieldOptions"
				:read_only="readOnly"
				:placeholder="__('Select field providing DocType (e.g. party_type)...')"
				hide-label
				allow-custom-value
			/>
		</CollapsibleSection>

		<!-- Step 2: Record / Source Document -->
		<CollapsibleSection
			:label="__('2. Record / Source Field')"
			:initial-collapsed="!!modelValue.record_field"
			:read-only="readOnly"
			class="mt-1"
		>
			<template #header-actions>
				<span v-if="modelValue.record_field" class="fxr-text-xs text-muted truncate ml-2">
					{{ modelValue.record_field }}
				</span>
			</template>
			<div class="d-flex fxr-gap-2">
				<SelectControl
					style="width: 80px"
					v-model="modelValue.record_source_type"
					:options="sourceTypeOptions"
					:read_only="readOnly"
					no-label
					@change="modelValue.record_field = ''"
				/>
				<ComboBoxControl
					v-if="modelValue.record_source_type !== 'expression'"
					class="flex-1 min-w-0"
					v-model="modelValue.record_field"
					:options="recordLinkOptions"
					:read_only="readOnly"
					:placeholder="
						modelValue.record_source_type === 'variable'
							? __('Search variable...')
							: __('Select field (e.g. party)...')
					"
					:allow-custom-value="modelValue.record_source_type === 'variable'"
					hide-label
				/>
				<DataControl
					v-else
					class="flex-1"
					v-model="modelValue.record_field"
					:read_only="readOnly"
					:placeholder="__('e.g. doc.party or row.party')"
					no-label
				/>
			</div>
		</CollapsibleSection>

		<!-- Step 3: Fetch Field -->
		<CollapsibleSection
			:label="__('3. Field to Fetch')"
			:initial-collapsed="false"
			:read-only="readOnly"
			class="mt-1 border-bottom-0"
		>
			<template #header-actions>
				<span v-if="modelValue.fetch_field" class="fxr-text-xs text-muted truncate ml-2">
					{{ modelValue.fetch_field }}
				</span>
			</template>
			<ComboBoxControl
				v-model="modelValue.fetch_field"
				:options="fetchFieldOptions"
				:read_only="readOnly || (modelValue.doctype_mode === 'static' && !modelValue.target_doctype)"
				:loading="fetchMetaLoading"
				:placeholder="fetchMetaLoading ? __('Loading metadata...') : __('Select field to fetch...')"
				:allow-custom-value="true"
				hide-label
			/>
		</CollapsibleSection>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useStore } from "../../../stores";
import ComboBoxControl from "../../ComboBoxControl.vue";
import SelectControl from "../../SelectControl.vue";
import DataControl from "../../DataControl.vue";
import CollapsibleSection from "../../CollapsibleSection.vue";
import { __ } from "../utils";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({}),
	},
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

const doctypeModeOptions = [
	{ value: "static", label: __("Fixed DocType") },
	{ value: "dynamic", label: __("Dynamic DocType From Field") },
];

const sourceTypeOptions = [
	{ value: "doc_field", label: __("Field") },
	{ value: "variable", label: __("Var") },
	{ value: "expression", label: __("Expr") },
];

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

const targetDocTypeHeader = computed(() => {
	if (props.modelValue.doctype_mode === "dynamic") {
		return props.modelValue.doctype_source
			? `Dynamic (${props.modelValue.doctype_source})`
			: __("Dynamic DocType");
	}
	return props.modelValue.target_doctype || "";
});

const prioritizedFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];

	const prioritizedTypes = ["Dynamic Link", "Link", "Data", "Select"];

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

const doctypeSourceFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];

	return fields
		.filter((f) => ["Link", "Dynamic Link", "Data", "Select", "DocType"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
			icon: "fa fa-i-cursor",
		}));
});

const recordLinkOptions = computed(() => {
	if (props.modelValue.record_source_type === "variable") {
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
	const linkedDt = props.modelValue.target_doctype;
	if (!linkedDt) return [];
	return store.get_fields_for_doctype(linkedDt, { valueMode: "fieldname" });
});

function onDoctypeModeChange() {
	if (props.modelValue.doctype_mode === "static") {
		props.modelValue.doctype_source = "";
	} else {
		props.modelValue.target_doctype = "";
	}
}

// Smart Auto-Detection for Dynamic Link and Link metadata
watch(
	() => props.modelValue.record_field,
	(newVal) => {
		if (!newVal) return;

		const opt = recordLinkOptions.value.find((o) => o.value === newVal);
		if (opt) {
			if (opt.fieldtype === "Dynamic Link" && opt.options) {
				props.modelValue.doctype_mode = "dynamic";
				props.modelValue.doctype_source = opt.options;
			} else if (opt.fieldtype === "Link" && opt.options && !props.modelValue.target_doctype) {
				props.modelValue.doctype_mode = "static";
				props.modelValue.target_doctype = opt.options;
			}
		}
	}
);

watch(
	() => props.modelValue.target_doctype,
	async (newVal, oldVal) => {
		if (!newVal) {
			if (props.modelValue.doctype_mode === "static") {
				props.modelValue.fetch_field = "";
			}
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
