<template>
	<div class="control-factory">
		<!-- Link -->
		<LinkControl
			v-if="df?.fieldtype === 'Link'"
			:df="df"
			:modelValue="modelValue"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<AutocompleteControl
			v-else-if="df?.fieldtype === 'Autocomplete'"
			:df="df"
			:modelValue="modelValue"
			:options="df?.options || df?.autocomplete_options"
			:get_options="get_options || df?.get_options"
			:doc="doc"
			:hideLabel="hideLabel"
			:hideDescription="hideDescription"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

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
				type="number"
				step="any"
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

		<!-- Text / Code / multiline -->
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

		<!-- MultiSelect -->
		<MultiSelectControl
			v-else-if="df?.fieldtype === 'MultiSelect'"
			:df="df"
			:modelValue="modelValue"
			:get_data="get_data || df?.get_data"
			:read_only="df.read_only"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- MultiSelectList -->
		<MultiSelectListControl
			v-else-if="df?.fieldtype === 'MultiSelectList'"
			:df="df"
			:modelValue="modelValue"
			:get_data="get_data || df?.get_data"
			:read_only="df.read_only"
			@update:modelValue="$emit('update:modelValue', $event)"
		/>

		<!-- MultiCheck -->
		<MultiCheckControl
			v-else-if="df?.fieldtype === 'MultiCheck'"
			:df="df"
			:modelValue="modelValue"
			:read_only="df.read_only"
			:hideLabel="hideLabel"
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
import { nextTick, onMounted, watch } from "vue";
import FlexiGrid from "./FlexiGrid.vue";
import MultiSelectListControl from "./MultiSelectListControl.vue";
import ResourceMapperControl from "./ResourceMapperControl.vue";
import TextGeneratorControl from "./TextGeneratorControl.vue";
import TimePickerControl from "./TimePickerControl.vue";

const props = defineProps({
	df: Object,
	modelValue: [String, Number, Boolean, Array, Object],
	doc: { type: Object, default: null }, // Context doc for autocomplete
	engine: { type: Object, default: null }, // Passed down to components like FlexiGrid
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
	get_options: { type: Function, default: null },
	get_data: { type: Function, default: null },
});

const emit = defineEmits(["update:modelValue"]);

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

		// Sanitize variable name to prevent injection/breaking templates
		// Reject common injection characters
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

		// Set cursor after the inserted variable
		nextTick(() => {
			input.focus();
			input.setSelectionRange(start + text.length, start + text.length);
		});
	}
}
</script>
