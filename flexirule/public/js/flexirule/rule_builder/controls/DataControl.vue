<!-- Used as Autocomplete, Barcode, Color, Currency, Data, Date, Duration, Link, Dynamic Link, Float, Int, Password, Percent, Time, Read Only, HTML Control -->
<script setup>
import { ref, onMounted, nextTick, useSlots } from "vue";
const emit = defineEmits(["update:modelValue"]);

const props = defineProps({
	df: Object,
	modelValue: [String, Number],
	read_only: Boolean,
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
});

const icon_ref = ref(null);
const phone_ref = ref(null);
let slots = useSlots();
let time_zone = ref("");
let placeholder = ref("");

if (props.df?.fieldtype === "Datetime") {
	let time_zone_text = frappe.boot.time_zone
		? frappe.boot.time_zone.user
		: frappe.sys_defaults.time_zone;
	time_zone.value = time_zone_text;
}

if (props.df?.fieldtype === "Color") {
	placeholder.value = __("Choose a color");
}
if (props.df?.fieldtype === "Icon") {
	placeholder.value = __("Choose an icon");
}

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

function evaluateMath(event) {
	const fieldtype = props.df?.fieldtype;
	if (!["Int", "Float", "Currency", "Percent"].includes(fieldtype)) return;

	let val = event.target.value;
	if (!val) return;

	try {
		if (/^[0-9+\-*/().\s]+$/.test(val)) {
			// eslint-disable-next-line no-new-func
			const evaluated = new Function(`return ${val}`)();
			if (!isNaN(evaluated)) {
				const finalVal = fieldtype === "Int" ? parseInt(evaluated) : parseFloat(evaluated);
				emit("update:modelValue", finalVal);
				event.target.value = finalVal;
			}
		} else {
			const finalVal = fieldtype === "Int" ? parseInt(val) : parseFloat(val);
			if (!isNaN(finalVal)) {
				emit("update:modelValue", finalVal);
			}
		}
	} catch (e) {
		const finalVal = fieldtype === "Int" ? parseInt(val) : parseFloat(val);
		if (!isNaN(finalVal)) {
			emit("update:modelValue", finalVal);
		}
	}
}

onMounted(() => {
	if (icon_ref.value) {
		icon_ref.value.innerHTML = frappe.utils.icon("folder-normal", "md");
	}
	if (phone_ref.value) {
		phone_ref.value.innerHTML = frappe.utils.icon("down", "sm");
	}
});
</script>

<template>
	<div class="fxr-control" :class="{ editable: slots.label }">
		<div
			class="fxr-input-group"
			:class="{
				'has-floating-label': df?.label && !hideLabel,
				'has-value': modelValue !== undefined && modelValue !== null && modelValue !== '',
			}"
		>
			<!-- label -->
			<div v-if="slots.label && !hideLabel" class="field-controls">
				<slot name="label" />
				<slot name="actions" />
			</div>
			<label v-else-if="df?.label && !hideLabel" class="fxr-label" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</label>

			<!-- data input -->
			<input
				v-if="slots.label"
				class="fxr-input"
				type="text"
				:style="{ height: df.fieldtype == 'Table MultiSelect' ? '42px' : '' }"
				:placeholder="__(placeholder)"
				readonly
			/>
			<input
				v-else
				class="fxr-input"
				:type="df?.fieldtype === 'Time' ? 'time' : 'text'"
				:step="df?.fieldtype === 'Time' ? '1' : undefined"
				:value="modelValue"
				:placeholder="__(df.placeholder || placeholder)"
				:disabled="read_only || df.read_only"
				@input="(event) => $emit('update:modelValue', event.target.value)"
				@blur="evaluateMath($event)"
				@keydown.enter="evaluateMath($event)"
				@dragover.prevent
				@drop="onDrop"
			/>
			<input
				v-if="slots.label && df.fieldtype === 'Barcode'"
				class="fxr-input mt-2"
				type="text"
				:style="{ height: '110px' }"
				readonly
			/>
		</div>

		<!-- description -->
		<div v-if="df.description && !hideDescription" class="fxr-description">
			{{ __(df.description) }}
		</div>

		<!-- timezone for datetime field -->
		<div v-if="time_zone" :class="['time-zone', !df.description ? 'mt-2' : '']">
			{{ time_zone }}
		</div>

		<!-- color selector icon -->
		<div class="selected-color no-value" />

		<!-- icon selector icon -->
		<div v-if="df.fieldtype == 'Icon'" class="selected-icon no-value" ref="icon_ref"></div>
		<!-- phone selector icon -->
		<div v-if="df.fieldtype == 'Phone'" class="selected-phone no-value" ref="phone_ref"></div>
	</div>
</template>

<style scoped>
.time-zone {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	font-style: italic;
	margin-top: var(--fxr-space-1);
}

.selected-color {
	background-color: transparent;
	top: 30px !important;
}

.selected-phone {
	top: 32px !important;
}
</style>
