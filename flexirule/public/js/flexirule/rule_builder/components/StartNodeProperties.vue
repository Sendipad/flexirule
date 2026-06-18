<!--
  StartNodeProperties - Properties panel for Start node

  This component handles the special Start node which uses Rule DocType fields,
  not Rule Action fields.
-->
<script setup>
import { computed, ref, watch, onMounted } from "vue";
import { useStore } from "../stores";
import ComboBoxControl from "../controls/ComboBoxControl.vue";
import ControlFactory from "../controls/ControlFactory.vue";

const props = defineProps({
	nodeData: Object,
	readOnly: Boolean,
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:field", "open:conditions"]);

const store = useStore();

// Trigger event options from store
const trigger_event_options = computed(() => store.trigger_event_options || []);
const trigger_type_options = computed(() => store.trigger_type_options || []);
const priority_options = Array.from({ length: 21 }, (_, i) => String(i));

const skip_roles = ref([]);
const permissions = ref([]);
const permission_meta = ref(null);
const pending_skip_role = ref("");
const is_manual_trigger = computed(() => props.nodeData?.trigger_event === "Manual");

function update_field(fieldname, value) {
	emit("update:field", fieldname, value);
}

// Check if conditions are configured
const has_conditions = computed(() => {
	const cond = props.nodeData?.trigger_condition;
	if (!cond) return false;
	if (typeof cond === "string") {
		return (
			cond !== "{}" &&
			cond !== "null" &&
			cond.trim() !== "" &&
			cond !== '{"op":"and","conditions":[]}'
		);
	}
	if (typeof cond === "object") {
		return cond.conditions && cond.conditions.length > 0;
	}
	return false;
});

const rule_status = computed(() => props.nodeData?.status || __("Draft"));

function normalize_skip_roles(value) {
	if (Array.isArray(value)) return value.filter(Boolean);
	return [];
}

function normalize_permissions(value) {
	if (!Array.isArray(value)) return [];
	return value.map((row) => ({
		role: row.role || "",
		can_execute: row.can_execute ? 1 : 0,
	}));
}

function default_permission_row() {
	const is_active = !!props.nodeData?.is_active;
	return {
		role: "System Manager",
		can_execute: 1,
	};
}

function ensure_default_permission() {
	if (props.readOnly) return;
	if (!permissions.value.length) {
		permissions.value = [default_permission_row()];
		update_field("permissions", permissions.value);
	}
}

function add_permission_row() {
	permissions.value.push({
		role: "",
		can_execute: 0,
	});
	update_field("permissions", permissions.value);
}

function remove_permission_row(idx) {
	permissions.value.splice(idx, 1);
	update_field("permissions", permissions.value);
}

function update_permission(idx, key, value) {
	if (!permissions.value[idx]) return;
	permissions.value[idx][key] = value;
	update_field("permissions", permissions.value);
}

function update_permission_role(idx, value) {
	if (!permissions.value[idx]) return;
	permissions.value[idx].role = value;
	update_field("permissions", permissions.value);
}

const controlRefs = ref([]);

async function validate() {
	const errors = [];

	if (!props.nodeData?.trigger_type) {
		errors.push(__("Trigger Type is required"));
	}
	if (!props.nodeData?.document_type) {
		errors.push(__("Document Type is required"));
	}

	const results = await Promise.all(
		(controlRefs.value || []).map((ref) => {
			if (ref && typeof ref.validate === "function") {
				return ref.validate();
			}
			return { valid: true };
		})
	);

	results.forEach((res) => {
		if (!res.valid) errors.push(...res.errors);
	});

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

function add_skip_role() {
	const role = pending_skip_role.value;
	if (!role) return;
	if (!skip_roles.value.includes(role)) {
		skip_roles.value.push(role);
		update_field("skip_for_roles", skip_roles.value);
	}
	pending_skip_role.value = "";
}

function remove_skip_role(role) {
	skip_roles.value = skip_roles.value.filter((r) => r !== role);
	update_field("skip_for_roles", skip_roles.value);
}

const permission_fields = computed(() => {
	const fields = permission_meta.value?.fields || [];
	return fields.filter((df) => {
		if (!df?.fieldname) return false;
		if (["name", "owner", "parent", "parenttype", "parentfield", "idx"].includes(df.fieldname))
			return false;
		return !["Section Break", "Column Break", "Tab Break"].includes(df.fieldtype);
	});
});

watch(
	() => props.nodeData?.skip_for_roles,
	(val) => {
		skip_roles.value = normalize_skip_roles(val);
	},
	{ immediate: true, deep: true }
);

watch(
	() => props.nodeData?.permissions,
	(val) => {
		permissions.value = normalize_permissions(val);
		ensure_default_permission();
	},
	{ immediate: true, deep: true }
);

watch(
	() => props.nodeData?.trigger_event,
	(val) => {
		if (val === "Manual") {
			update_field("priority", "0");
		}
	},
	{ immediate: true }
);

onMounted(async () => {
	if (!frappe.get_meta("Rule Permission")) {
		await frappe.model.with_doctype("Rule Permission");
	}
	permission_meta.value = frappe.get_meta("Rule Permission");
});
</script>

<template>
	<div class="start-node-properties">
		<!-- Rule Info -->
		<div class="form-group">
			<label class="control-label">{{ __("Rule Name") }}</label>
			<input class="form-control" type="text" disabled :value="nodeData?.rule_name" />
		</div>

		<!-- Trigger Type -->
		<div class="form-group" :class="{ 'has-error': showValidation && !nodeData?.trigger_type }">
			<label class="control-label">{{ __("Trigger Type") }}</label>
			<select
				class="form-control"
				:value="nodeData?.trigger_type"
				:disabled="readOnly"
				@change="update_field('trigger_type', $event.target.value)"
			>
				<option v-for="opt in trigger_type_options" :key="opt" :value="opt">
					{{ __(opt) }}
				</option>
			</select>
		</div>

		<!-- Document Type -->
		<div class="form-group">
			<label class="control-label">{{ __("Document Type") }}</label>
			<ComboBoxControl
				ref="controlRefs"
				:df="{ fieldtype: 'Link', options: 'DocType', label: '', reqd: 1 }"
				:modelValue="nodeData?.document_type"
				:read_only="readOnly"
				:hideLabel="true"
				:showValidation="showValidation"
				@update:modelValue="(val) => update_field('document_type', val)"
			/>
		</div>

		<!-- Status & Version -->
		<div class="form-row">
			<div class="form-group col-6">
				<label class="control-label">{{ __("Status") }}</label>
				<div :class="['status-badge', rule_status.toLowerCase()]">
					{{ rule_status }}
				</div>
			</div>
			<div class="form-group col-6">
				<label class="control-label">{{ __("Version") }}</label>
				<div class="version-badge">v{{ nodeData?.version || 1 }}</div>
			</div>
		</div>

		<!-- Trigger Event -->
		<div class="form-group">
			<label class="control-label">{{ __("Trigger Event") }}</label>
			<select
				class="form-control"
				:value="nodeData?.trigger_event"
				@change="update_field('trigger_event', $event.target.value)"
				:disabled="readOnly"
			>
				<option v-for="opt in trigger_event_options" :key="opt" :value="opt">
					{{ opt }}
				</option>
			</select>
		</div>

		<!-- Trigger Condition -->
		<div class="form-group">
			<label class="control-label">{{ __("Trigger Condition (Logic)") }}</label>
			<div class="description text-muted mb-2">
				{{ __("Define complex logic conditions for when this rule should trigger.") }}
			</div>

			<button class="btn btn-default btn-sm w-100" @click="emit('open:conditions')">
				<i class="fa fa-code-fork"></i>
				{{ __("Open Condition Builder") }}
			</button>

			<div v-if="has_conditions" class="mt-2 text-success small">
				<i class="fa fa-check-circle"></i>
				{{ __("Conditions Configured") }}
			</div>
		</div>

		<!-- Priority -->
		<div class="form-group">
			<label class="control-label">{{ __("Priority") }}</label>
			<select
				class="form-control"
				:value="nodeData?.priority"
				@change="update_field('priority', $event.target.value)"
				:disabled="readOnly || is_manual_trigger"
			>
				<option v-for="opt in priority_options" :key="opt" :value="opt">
					{{ opt }}
				</option>
			</select>
			<div v-if="is_manual_trigger" class="description text-muted mt-1">
				{{ __("Manual trigger rules must use priority 0.") }}
			</div>
		</div>

		<!-- Execution Mode -->
		<div class="form-group">
			<label class="control-label">{{ __("Execution Mode") }}</label>
			<select
				class="form-control"
				:value="nodeData?.execution_mode"
				@change="update_field('execution_mode', $event.target.value)"
				:disabled="readOnly"
			>
				<option value="Synchronous">{{ __("Synchronous") }}</option>
				<option value="Asynchronous">{{ __("Asynchronous") }}</option>
			</select>
		</div>

		<!-- Max Execution Time -->
		<div class="form-group">
			<label class="control-label">{{ __("Max Execution Time (seconds)") }}</label>
			<input
				type="number"
				class="form-control"
				:value="nodeData?.max_execution_time"
				:disabled="readOnly"
				@change="update_field('max_execution_time', Number($event.target.value))"
			/>
		</div>

		<!-- Debug Mode -->
		<div class="form-group inline-field">
			<label class="control-label">{{ __("Debug Mode") }}</label>
			<input
				type="checkbox"
				:checked="!!nodeData?.debug_mode"
				:disabled="readOnly"
				@change="update_field('debug_mode', $event.target.checked ? 1 : 0)"
			/>
		</div>

		<!-- Exposed As Sub-Rule -->
		<div class="form-group inline-field">
			<label class="control-label">{{ __("Exposed As Sub-Rule") }}</label>
			<input
				type="checkbox"
				:checked="!!nodeData?.exposed_as_subrule"
				:disabled="readOnly"
				@change="update_field('exposed_as_subrule', $event.target.checked ? 1 : 0)"
			/>
		</div>

		<!-- Description -->
		<div class="form-group">
			<label class="control-label">{{ __("Description") }}</label>
			<textarea
				class="form-control"
				rows="2"
				:disabled="readOnly"
				:value="nodeData?.description"
				@change="update_field('description', $event.target.value)"
			></textarea>
		</div>

		<!-- Skip for Roles -->
		<div class="form-group">
			<label class="control-label">{{ __("Skip for Roles") }}</label>
			<div class="role-picker">
				<ComboBoxControl
					:df="{ fieldtype: 'Link', options: 'Role', label: '' }"
					:modelValue="pending_skip_role"
					:read_only="readOnly"
					:hideLabel="true"
					@update:modelValue="(val) => (pending_skip_role = val)"
				/>
				<button class="btn btn-xs btn-default" @click="add_skip_role" :disabled="readOnly">
					{{ __("Add") }}
				</button>
			</div>
			<div class="role-tags" v-if="skip_roles.length">
				<span v-for="role in skip_roles" :key="role" class="role-tag">
					{{ role }}
					<button
						v-if="!readOnly"
						class="btn btn-xs btn-link text-danger"
						@click="remove_skip_role(role)"
					>
						×
					</button>
				</span>
			</div>
		</div>

		<!-- Rule Permissions -->
		<div class="form-group">
			<div class="section-header">
				<label class="control-label">{{ __("Rule Permissions") }}</label>
				<button v-if="!readOnly" class="btn btn-xs btn-link" @click="add_permission_row">
					<i class="fa fa-plus"></i> {{ __("Add") }}
				</button>
			</div>
			<div class="perm-table" v-if="permission_fields.length">
				<div class="perm-row perm-header">
					<span v-for="df in permission_fields" :key="df.fieldname">
						{{ __(df.label || df.fieldname) }}
					</span>
					<span></span>
				</div>
				<div v-for="(row, idx) in permissions" :key="idx" class="perm-row">
					<div v-for="df in permission_fields" :key="df.fieldname">
						<ControlFactory
							:df="{ ...df, read_only: readOnly }"
							:modelValue="row[df.fieldname]"
							:hideLabel="true"
							:hideDescription="true"
							@update:modelValue="(val) => update_permission(idx, df.fieldname, val)"
						/>
					</div>
					<button
						v-if="!readOnly"
						class="btn btn-xs btn-link text-danger"
						@click="remove_permission_row(idx)"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
				<div v-if="!permissions.length" class="text-muted small">
					{{ __("No permissions configured.") }}
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.start-node-properties {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.form-group {
	margin-bottom: 0;
}

.control-label {
	font-size: 11px;
	font-weight: 500;
	margin-bottom: 4px;
	color: var(--text-muted);
	display: block;
}

.description {
	font-size: 11px;
}

.form-control {
	width: 100%;
	padding: 6px 10px;
	border: 1px solid var(--border-color);
	border-radius: 4px;
	font-size: 13px;
}

.text-mono {
	font-family: monospace;
	font-size: 11px;
}

.btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
}

.w-100 {
	width: 100%;
}

.mt-2 {
	margin-top: 8px;
}

.mb-2 {
	margin-bottom: 8px;
}

.inline-field {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
}

.role-picker {
	display: flex;
	gap: 8px;
	align-items: center;
}

.role-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	margin-top: 6px;
}

.role-tag {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 2px 6px;
	border-radius: 12px;
	background: var(--bg-light-gray, #f5f5f5);
	font-size: 11px;
}

.section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.perm-table {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.perm-row {
	display: grid;
	grid-template-columns: 1.6fr 0.7fr auto;
	gap: 6px;
	align-items: center;
}

.perm-header {
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted);
}
</style>
