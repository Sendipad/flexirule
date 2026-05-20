<template>
	<div class="control-factory">
		<!-- Unified ComboBox for Link, Autocomplete, and FieldPicker -->
		<template
			v-if="
				['Link', 'Dynamic Link', 'Autocomplete', 'FieldPicker', 'DocField'].includes(
					df?.fieldtype
				) || df?.options === 'DocField'
			"
		>
			<ComboBoxControl
				:df="df"
				:modelValue="modelValue"
				:rule="engine?.rule_doc"
				:doctype="comboDoctype"
				:options="comboOptions"
				:get_query="comboGetQuery"
				:filters="df?.get_query ? null : df?.filters"
				:context="
					['FieldPicker', 'DocField'].includes(df?.fieldtype) ||
					df?.options === 'DocField'
						? df?.context || doc
						: null
				"
				:trigger="df?.fieldtype === 'FieldPicker' ? 'button' : 'input'"
				:hideLabel="hideLabel"
				:hideDescription="hideDescription"
				:read_only="df?.read_only"
				@update:modelValue="$emit('update:modelValue', $event)"
			/>
		</template>

		<!-- Select -->
		<SelectControl
			v-else-if="df?.fieldtype === 'Select'"
			:df="df"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Check -->
		<CheckControl
			v-else-if="df?.fieldtype === 'Check'"
			:df="df"
			:modelValue="Boolean(modelValue)"
			:hideLabel="hideLabel"
			@update:modelValue="$emit('update:modelValue', $event ? 1 : 0)"
		/>

		<!-- Number (Int, Float, Currency, Percent) -->
		<div
			v-else-if="['Int', 'Float', 'Currency', 'Percent'].includes(df?.fieldtype)"
			class="control frappe-control"
		>
			<div
				v-if="df.label && !hideLabel"
				class="control-label label"
				:class="{ reqd: df.reqd }"
			>
				{{ __(df.label) }}
			</div>
			<input
				type="text"
				class="form-control input-sm"
				:value="modelValue"
				:disabled="df.read_only"
				:aria-label="__(df.label)"
				@input="
					$emit(
						'update:modelValue',
						df.fieldtype === 'Int'
							? parseInt($event.target.value)
							: parseFloat($event.target.value)
					)
				"
			/>
			<div v-if="df.description" class="description text-muted mt-1">
				{{ __(df.description) }}
			</div>
		</div>

		<!-- Date / Datetime -->
		<TimePickerControl
			v-else-if="['Date', 'Datetime'].includes(df?.fieldtype)"
			:df="df"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Time -->
		<div v-else-if="df?.fieldtype === 'Time'" class="control frappe-control">
			<div
				v-if="df.label && !hideLabel"
				class="control-label label"
				:class="{ reqd: df.reqd }"
			>
				{{ __(df.label) }}
			</div>
			<input
				type="time"
				step="1"
				class="form-control input-sm"
				:value="modelValue"
				:disabled="df.read_only"
				:aria-label="__(df.label)"
				@input="$emit('update:modelValue', $event.target.value)"
			/>
			<div v-if="df.description" class="description text-muted mt-1">
				{{ __(df.description) }}
			</div>
		</div>

		<!-- Text / Code / JSON / multiline -->
		<div
			v-else-if="
				[
					'Text',
					'Small Text',
					'Text Editor',
					'Code',
					'JSON',
					'HTML Editor',
					'Markdown Editor',
					'Long Text',
				].includes(df?.fieldtype)
			"
			class="control frappe-control"
		>
			<div
				v-if="df.label && !hideLabel"
				class="control-label label"
				:class="{ reqd: df.reqd }"
			>
				{{ __(df.label) }}
			</div>
			<textarea
				class="form-control"
				rows="3"
				:value="modelValue"
				:disabled="df.read_only"
				:aria-label="__(df.label)"
				@input="$emit('update:modelValue', $event.target.value)"
				@dragover.prevent
				@drop="onDrop"
			></textarea>
			<div v-if="df.description" class="description text-muted mt-1">
				{{ __(df.description) }}
			</div>
		</div>

		<!-- Table -->
		<FlexiGrid
			v-else-if="df?.fieldtype === 'Table'"
			:df="df"
			:modelValue="modelValue"
			:engine="engine"
			:read_only="df.read_only"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- MultiSelect / MultiCheck / MultiFieldPicker -->
		<MultiSelectList
			v-else-if="
				['MultiSelect', 'MultiFieldPicker', 'MultiSelectList', 'MultiCheck'].includes(
					df?.fieldtype
				)
			"
			:displayMode="getMultiListDisplayMode(df)"
			:columns="df?.fieldtype === 'MultiCheck' ? 2 : undefined"
			:df="df"
			:modelValue="modelValue"
			:get_data="get_data || df?.get_data"
			:documentType="
				df?.fieldtype === 'MultiFieldPicker'
					? df?.target_doctype || engine?.rule_doc?.document_type
					: undefined
			"
			:read_only="df.read_only"
			:hideLabel="hideLabel"
			:expanded="df?.fieldtype === 'MultiCheck' ? !hideLabel : undefined"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Specialized / High-level controls -->
		<ResourceMapperControl
			v-else-if="df?.fieldtype === 'Resource Mapper'"
			:df="df"
			:modelValue="modelValue"
			:targetDoctype="df?.target_doctype || ''"
			:targetFields="df?.target_fields || []"
			:sourceOptions="df?.source_options || []"
			:read_only="df?.read_only"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<TextGeneratorControl
			v-else-if="df?.fieldtype === 'Text Generator'"
			:df="df"
			:modelValue="modelValue"
			:read_only="df?.read_only"
			:variableOptions="df?.variable_options || []"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<FlexValueControl
			v-else-if="df?.fieldtype === 'Structured Value'"
			:df="df"
			:modelValue="modelValue"
			:read_only="df?.read_only"
			:variableOptions="df?.variable_options || []"
			:fieldType="df?.target_fieldtype || 'Data'"
			:compact="df?.compact || false"
			:placeholder="df?.placeholder || ''"
			:options="df?.options"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Attach / Attach Image fallback (using DataControl for now) -->
		<DataControl
			v-else-if="['Attach', 'Attach Image'].includes(df?.fieldtype)"
			:df="df"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Default (Data, Duration, Valid types defaulting to text) -->
		<DataControl
			v-else-if="!['Table', 'Signature', 'Button', 'Heading'].includes(df?.fieldtype)"
			:df="df || { fieldtype: 'Data' }"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- Fallback for unsupported/unsafe types -->
		<div v-else class="text-muted small p-2 border rounded bg-light">
			{{ df?.fieldtype }} {{ __("not supported in this context") }}
		</div>
	</div>
</template>

<script setup>
import { nextTick, onMounted, watch, computed, defineAsyncComponent } from "vue";
import ComboBoxControl from "./ComboBoxControl.vue";
import MultiSelectList from "./MultiSelectList.vue";
import TimePickerControl from "./TimePickerControl.vue";
import SelectControl from "./SelectControl.vue";
import CheckControl from "./CheckControl.vue";
import DataControl from "./DataControl.vue";
import ResourceMapperControl from "./ResourceMapperControl.vue";
import TextGeneratorControl from "./TextGeneratorControl.vue";

// Use async components for potential circular dependencies
const FlexiGrid = defineAsyncComponent(() => import("./FlexiGrid.vue"));
const FlexValueControl = defineAsyncComponent(() => import("./FlexValueControl.vue"));

const props = defineProps({
	df: Object,
	modelValue: [String, Number, Boolean, Array, Object],
	doc: { type: Object, default: null }, // Context doc for autocomplete
	options: { type: Array, default: null }, // Direct options override
	engine: { type: Object, default: null }, // Passed down to components like FlexiGrid
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
	get_options: { type: Function, default: null },
	get_data: { type: Function, default: null },
});

const emit = defineEmits(["update:modelValue"]);

// ── DocField / FieldPicker helpers ────────────────────────────────────────────

const isDocFieldType = computed(
	() =>
		["DocField", "FieldPicker"].includes(props.df?.fieldtype) ||
		props.df?.options === "DocField"
);

const docFieldTargetDoctype = computed(() => {
	if (!isDocFieldType.value) return null;
	if (props.df?.target_doctype) return props.df.target_doctype;
	const opt = props.df?.options;
	if (
		typeof opt === "string" &&
		opt &&
		!opt.startsWith("vars.") &&
		!opt.startsWith("doc.") &&
		opt !== "DocField" &&
		opt !== "Field Picker" &&
		opt !== "Variables"
	) {
		return opt;
	}
	return props.engine?.rule_doc?.document_type || null;
});

const comboDoctype = computed(() => {
	const ft = props.df?.fieldtype;
	if (ft === "Link") return props.df?.options || props.df?.target_doctype || null;
	if (ft === "Dynamic Link") return props.doc?.[props.df?.options] || "";
	return null;
});

const comboOptions = computed(() => {
	if (isDocFieldType.value) {
		if (Array.isArray(props.df?.options) && props.df.options.length > 0) {
			return props.df.options;
		}
		return [];
	}
	return (
		props.df?.autocomplete_options ||
		(["Autocomplete", "Select"].includes(props.df?.fieldtype) ? props.df?.options : null) ||
		props.options ||
		[]
	);
});

const comboGetQuery = computed(() => {
	if (!isDocFieldType.value) {
		return props.get_options || props.df?.get_options || null;
	}
	if (Array.isArray(props.df?.options) && props.df.options.length > 0) {
		return null;
	}
	const targetDoctype = docFieldTargetDoctype.value;
	if (!targetDoctype) return null;
	return async (search_term) => {
		try {
			const fields = await flexirule.utils.get_doctype_fields(targetDoctype);
			if (!search_term) return fields;
			const q = search_term.toLowerCase();
			return fields.filter(
				(f) =>
					(f.label || "").toLowerCase().includes(q) ||
					(f.value || "").toLowerCase().includes(q) ||
					(f.description || "").toLowerCase().includes(q)
			);
		} catch (e) {
			console.error("FlexiRule: DocField options fetch failed for", targetDoctype, e);
			return [];
		}
	};
});

function getMultiListDisplayMode(df) {
	if (df?.displayMode) return df.displayMode;
	if (df?.fieldtype === "MultiSelect" || df?.fieldtype === "MultiFieldPicker") return "badges";
	if (df?.fieldtype === "MultiSelectList") return "list";
	if (df?.fieldtype === "MultiCheck") return "columns";
	return "badges";
}

onMounted(() => {
	check_default();
});

watch(
	() => props.df?.default,
	() => {
		check_default();
	}
);

function check_default() {
	if (props.modelValue === undefined || props.modelValue === null || props.modelValue === "") {
		if (props.df?.default !== undefined && props.df?.default !== null) {
			emit("update:modelValue", props.df.default);
		}
	}
}

function onDrop(event) {
	let variable = event.dataTransfer.getData("application/x-flexirule-variable");
	if (variable) {
		event.preventDefault();
		if (/[{}"']/.test(variable)) {
			console.warn("FlexiRule: Rejected unsafe variable name drop:", variable);
			return;
		}
		const text = `{{ ${variable} }}`;
		const input = event.target;
		const start = input.selectionStart;
		const end = input.selectionEnd;
		const val = props.modelValue || "";
		const newVal = val.substring(0, start) + text + val.substring(end);
		emit("update:modelValue", newVal);
		nextTick(() => {
			input.focus();
			input.setSelectionRange(start + text.length, start + text.length);
		});
	}
}
</script>
