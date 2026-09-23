<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Operation") }}</label>
			<select v-model="localState.operation" class="form-control form-control-sm" :disabled="readOnly">
				<option value="field">{{ __("Document Field") }}</option>
				<option value="variable">{{ __("Rule Variable") }}</option>
				<option value="static">{{ __("Static Value") }}</option>
				<option value="system_context">{{ __("System Context") }}</option>
			</select>
		</div>

		<div v-if="['field', 'variable', 'old_field'].includes(localState.operation)" class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Path / Fieldname") }}</label>

			<ComboBoxControl
				v-model="localState.path"
				:options="variableOptions"
				:doctype="doctype"
				:read_only="readOnly"
				class="w-100"
			/>
		</div>

		<div v-if="localState.operation === 'static'" class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("Literal Value") }}</label>
			<input
				v-model="localState.value"
				type="text"
				class="form-control form-control-sm"
				:disabled="readOnly"
			/>
		</div>

		<div v-if="localState.operation === 'system_context'" class="d-flex flex-column fxr-gap-2">
			<div class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Context Token") }}</label>
				<select v-model="localState.sys_token" class="form-control form-control-sm" :disabled="readOnly">
					<option value="user">{{ __("Current User ID") }}</option>
					<option value="role_check">{{ __("Role Membership Check") }}</option>
				</select>
			</div>

			<div v-if="localState.sys_token === 'role_check'" class="form-group mb-0">
				<label class="fxr-label-sm">{{ __("Role Name") }}</label>
				<input
					v-model="localState.sys_role"
					type="text"
					class="form-control form-control-sm"
					placeholder="e.g. Accounts Manager"
					:disabled="readOnly"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import ComboBoxControl from "../../ComboBoxControl.vue";
import { __ } from "../utils";

const props = defineProps({
	modelValue: { type: Object, default: () => ({}) },
	doctype: { type: String, default: "" },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: () => [] },
});

const localState = props.modelValue;
</script>
