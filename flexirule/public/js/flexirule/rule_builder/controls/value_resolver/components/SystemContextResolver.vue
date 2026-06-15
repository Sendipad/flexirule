<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("System Token") }}</label>
		<select class="fxr-select" v-model="modelValue.sys_token" :disabled="readOnly">
			<option value="user">{{ __("Current User") }}</option>
			<option value="role_check">{{ __("Has Role?") }}</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2" v-if="modelValue.sys_token === 'role_check'">
		<label class="fxr-label-sm">{{ __("Role Name") }}</label>
		<input
			type="text"
			class="fxr-input"
			v-model="modelValue.sys_role"
			:disabled="readOnly"
			:placeholder="__('e.g. System Manager')"
		/>
	</div>
</template>

<script setup>
import { __ } from "../utils";

defineProps({
	modelValue: Object,
	readOnly: Boolean,
});
</script>
