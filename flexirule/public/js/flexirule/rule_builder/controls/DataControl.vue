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
	<div class="control frappe-control" :class="{ editable: slots.label }">
		<!-- label -->
		<div v-if="slots.label && !hideLabel" class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<div
			v-else-if="df?.label && !hideLabel"
			class="control-label label"
			:class="{ reqd: df.reqd }"
		>
			{{ __(df.label) }}
		</div>

		<!-- data input -->
		<input
			v-if="slots.label"
			class="form-control"
			type="text"
			:style="{ height: df.fieldtype == 'Table MultiSelect' ? '42px' : '' }"
			:placeholder="__(placeholder)"
			readonly
		/>
		<input
			v-else
			class="form-control"
			type="text"
			:value="modelValue"
			:disabled="read_only || df.read_only"
			@input="(event) => $emit('update:modelValue', event.target.value)"
			@dragover.prevent
			@drop="onDrop"
		/>
		<input
			v-if="slots.label && df.fieldtype === 'Barcode'"
			class="mt-2 form-control"
			type="text"
			:style="{ height: '110px' }"
			readonly
		/>

		<!-- description -->
		<div v-if="df.description && !hideDescription" class="mt-2 description">
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

<style lang="scss" scoped>
.selected-color {
	background-color: transparent;
	top: 30px !important;
}

.selected-phone {
	top: 32px !important;
}
</style>
