<template>
	<div class="fxr-control">
		<div
			class="fxr-input-group"
			:class="{
				'has-floating-label': df?.label && !hideLabel,
				'has-value': modelValue !== undefined && modelValue !== null && modelValue !== '',
			}"
		>
			<!-- label -->
			<label v-if="df?.label && !hideLabel" class="fxr-label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</label>

			<!-- Single Date/Datetime Input -->
			<div v-if="!isRange" class="time-picker-container">
				<input
					:type="inputType"
					class="form-control input-sm"
					:value="formattedValue"
					:disabled="read_only || df.read_only"
					:aria-label="__(df.label)"
					:min="df.min_value"
					:max="df.max_value"
					@input="handleSingleInput"
				/>
			</div>

			<!-- Range Input -->
			<div v-else class="time-picker-container range-input">
				<div class="range-fields">
					<div class="range-field">
						<label class="range-label">{{ __("From") }}</label>
						<input
							:type="inputType"
							class="form-control input-sm"
							:value="formattedStartValue"
							:disabled="read_only || df.read_only"
							:aria-label="__('{0} From', [__(df.label)])"
							:min="df.min_value"
							:max="df.max_value"
							@input="handleRangeStartInput"
						/>
					</div>
					<div class="range-field">
						<label class="range-label">{{ __("To") }}</label>
						<input
							:type="inputType"
							class="form-control input-sm"
							:value="formattedEndValue"
							:disabled="read_only || df.read_only"
							:aria-label="__('{0} To', [__(df.label)])"
							:min="df.min_value"
							:max="df.max_value"
							@input="handleRangeEndInput"
						/>
					</div>
				</div>
			</div>
		</div>

		<!-- description -->
		<div v-if="df.description && !hideDescription" class="fxr-description mt-2">
			{{ __(df.description) }}
		</div>

		<!-- timezone for datetime field -->
		<div
			v-if="time_zone && df.fieldtype === 'Datetime'"
			:class="['time-zone', !df.description ? 'mt-2' : '']"
		>
			{{ time_zone }}
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";

const emit = defineEmits(["update:modelValue"]);

const props = defineProps({
	df: Object,
	modelValue: [String, Array, Object],
	read_only: Boolean,
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

// Timezone for datetime fields
const time_zone = ref("");
if (props.df?.fieldtype === "Datetime") {
	let time_zone_text = frappe.boot.time_zone
		? frappe.boot.time_zone.user
		: frappe.sys_defaults.time_zone;
	time_zone.value = time_zone_text;
}

// Determine if this is a range input based on field options or a special flag
const isRange = computed(() => {
	return (
		props.df?.options === "range" ||
		props.df?.is_range === true ||
		(Array.isArray(props.modelValue) && props.modelValue.length === 2)
	);
});

// Input type based on fieldtype
const inputType = computed(() => {
	switch (props.df?.fieldtype) {
		case "Date":
			return "date";
		case "Datetime":
			return "datetime-local";
		case "Time":
			return "time";
		default:
			return "datetime-local";
	}
});

// Format value for display
const formattedValue = computed(() => {
	if (!props.modelValue) return "";

	// For datetime-local, ensure proper format
	if (props.df?.fieldtype === "Datetime" && props.modelValue) {
		try {
			// Convert various datetime formats to datetime-local format (YYYY-MM-DDTHH:mm)
			const date = new Date(props.modelValue);
			if (!isNaN(date.getTime())) {
				return date.toISOString().slice(0, 16);
			}
		} catch (e) {
			console.warn("Invalid datetime format:", props.modelValue);
		}
	}

	return props.modelValue;
});

// For range inputs
const formattedStartValue = computed(() => {
	if (!isRange.value || !Array.isArray(props.modelValue)) return "";
	return formatDateTimeValue(props.modelValue[0]);
});

const formattedEndValue = computed(() => {
	if (!isRange.value || !Array.isArray(props.modelValue)) return "";
	return formatDateTimeValue(props.modelValue[1]);
});

function formatDateTimeValue(value) {
	if (!value) return "";

	if (props.df?.fieldtype === "Datetime") {
		try {
			const date = new Date(value);
			if (!isNaN(date.getTime())) {
				return date.toISOString().slice(0, 16);
			}
		} catch (e) {
			console.warn("Invalid datetime format:", value);
		}
	}

	return value;
}

function handleSingleInput(event) {
	let value = event.target.value;

	// For datetime-local, convert back to standard format if needed
	if (props.df?.fieldtype === "Datetime" && value) {
		// datetime-local format is already good, but we might want to store as ISO string
		const date = new Date(value);
		if (!isNaN(date.getTime())) {
			value = date.toISOString();
		}
	}

	emit("update:modelValue", value);
}

function handleRangeStartInput(event) {
	let startValue = event.target.value;

	if (props.df?.fieldtype === "Datetime" && startValue) {
		const date = new Date(startValue);
		if (!isNaN(date.getTime())) {
			startValue = date.toISOString();
		}
	}

	const currentValue = Array.isArray(props.modelValue) ? props.modelValue : ["", ""];
	const newValue = [startValue, currentValue[1]];

	emit("update:modelValue", newValue);
}

function handleRangeEndInput(event) {
	let endValue = event.target.value;

	if (props.df?.fieldtype === "Datetime" && endValue) {
		const date = new Date(endValue);
		if (!isNaN(date.getTime())) {
			endValue = date.toISOString();
		}
	}

	const currentValue = Array.isArray(props.modelValue) ? props.modelValue : ["", ""];
	const newValue = [currentValue[0], endValue];

	emit("update:modelValue", newValue);
}

// Support for drag-and-drop variables
function onDrop(event) {
	let variable = event.dataTransfer.getData("application/x-flexirule-variable");
	if (variable) {
		event.preventDefault();

		// Sanitize variable name to prevent injection/breaking templates
		if (/[{}"']/.test(variable)) {
			console.warn("FlexiRule: Rejected unsafe variable name drop:", variable);
			return;
		}

		const text = `{{ ${variable} }}`;
		const input = event.target;
		const start = input.selectionStart;
		const end = input.selectionEnd;
		const val = input.value || "";
		const newVal = val.substring(0, start) + text + val.substring(end);

		// Update the appropriate field
		if (isRange.value) {
			const isStartField =
				input === input.closest(".range-field").querySelector("input:first-of-type");
			if (isStartField) {
				handleRangeStartInput({ target: { value: newVal } });
			} else {
				handleRangeEndInput({ target: { value: newVal } });
			}
		} else {
			handleSingleInput({ target: { value: newVal } });
		}

		// Set cursor after the inserted variable
		nextTick(() => {
			input.focus();
			input.setSelectionRange(start + text.length, start + text.length);
		});
	}
}
</script>

<style lang="scss" scoped>
.time-picker-container {
	&.range-input {
		.range-fields {
			display: flex;
			gap: 1rem;
			align-items: flex-start;

			.range-field {
				flex: 1;

				.range-label {
					display: block;
					font-size: 0.875rem;
					font-weight: 500;
					color: #6c757d;
					margin-bottom: 0.25rem;
				}
			}
		}
	}
}

.time-zone {
	font-size: 0.75rem;
	color: #6c757d;
	margin-top: 0.25rem;
}

@media (max-width: 768px) {
	.range-input .range-fields {
		flex-direction: column;
		gap: 0.5rem;
	}
}
</style>
