<template>
	<div class="d-flex flex-column fxr-gap-1">
		<SelectControl
			v-model="modelValue.sys_token"
			:options="tokenOptions"
			:read_only="readOnly"
			:df="{ label: __('System Token') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2" v-if="modelValue.sys_token === 'role_check'">
		<ComboBoxControl
			v-model="modelValue.sys_role"
			doctype="Role"
			:read_only="readOnly"
			:df="{ label: __('Role Name') }"
			:placeholder="__('e.g. System Manager')"
		/>
	</div>
</template>

<script setup>
import { __ } from "../utils";
import SelectControl from "../../SelectControl.vue";
import ComboBoxControl from "../../ComboBoxControl.vue";

const tokenOptions = [
	{ value: "user", label: __("Current User") },
	{ value: "role_check", label: __("Has Role?") },
];

defineProps({
	modelValue: Object,
	readOnly: Boolean,
});
</script>
