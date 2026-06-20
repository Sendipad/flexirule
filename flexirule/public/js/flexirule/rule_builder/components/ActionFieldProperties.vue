<!--
  ActionFieldProperties - DocField-driven property panel for Rule Action nodes

  Renders fields dynamically from Rule Action DocType metadata, respecting:
   - depends_on
   - mandatory_depends_on
   - read_only_depends_on
   - hidden

  Follows Frappe Form Builder patterns.
-->
<script setup>
import { ref, computed, onMounted, onBeforeUpdate } from "vue";
import { useStore } from "../stores";
import ControlFactory from "../controls/ControlFactory.vue";
import ComboBoxControl from "../controls/ComboBoxControl.vue";
import {
	getActionTypeOptions,
	getFieldLabel,
	getOperationOptions,
	normalizeActionType,
} from "../../core/contracts";
import { useNodeConfigPolicy } from "../composables/useNodeConfigPolicy";
import { toCodeString, fromCodeString, isJsonField } from "../utils/serialization";

const props = defineProps({
	nodeData: Object,
	readOnly: Boolean,
	showValidation: { type: Boolean, default: false },
	// New props for reusability
	includeFields: { type: Array, default: null },
	excludeFields: { type: Array, default: () => [] },
	section: { type: String, default: null },
});

const emit = defineEmits(["update:field", "open:conditions", "open:config"]);

const store = useStore();
const { getPolicyField, getPolicyValue } = useNodeConfigPolicy({
	actionType: () => props.nodeData?.action_type || "",
	operation: () => props.nodeData?.operation || "",
	processName: () => props.nodeData?.process_name || "",
});

// Layout fields to skip
const LAYOUT_FIELDS = ["Section Break", "Column Break", "Tab Break"];

// Get Rule Action DocType meta
const rule_action_meta = computed(() => {
	return frappe.get_meta("Rule Action");
});

// Get fields from meta, filtering based on props
const doc_fields = computed(() => {
	const meta = rule_action_meta.value;
	if (!meta || !meta.fields) return [];

	let fields = [];
	if (props.section) {
		let in_section = false;
		for (const fieldname of meta.field_order) {
			const df = meta.fields.find((f) => f.fieldname === fieldname);
			if (!df) continue;
			if (df.fieldtype === "Section Break") {
				if (df.fieldname === props.section) {
					in_section = true;
					continue;
				} else if (in_section) {
					break;
				}
			}
			if (in_section) fields.push(df);
		}
	} else if (props.includeFields) {
		fields = props.includeFields
			.map((fn) => meta.fields.find((f) => f.fieldname === fn))
			.filter(Boolean);
	} else {
		fields = meta.fields;
	}

	return fields
		.filter((df) => {
			// Skip layout fields
			if (LAYOUT_FIELDS.includes(df.fieldtype)) return false;

			// Skip excluded fields
			if (props.excludeFields.includes(df.fieldname)) return false;

			// Skip always hidden fields
			if (df.hidden) return false;
			if (getPolicyValue(df.fieldname, "hidden", false)) return false;

			return true;
		})
		.map((df) => {
			let resolved = { ...df };
			const actionType = normalizeActionType(props.nodeData?.action_type);
			const policyLabel = actionType
				? getFieldLabel(actionType, df.fieldname, {
						operation: props.nodeData?.operation,
						processName: props.nodeData?.process_name,
				  })
				: null;
			if (resolved.fieldname === "action_type") {
				resolved = {
					...resolved,
					options: getActionTypeOptions().join("\n"),
				};
			}
			resolved = getPolicyField(resolved.fieldname, resolved);
			// Inject get_query for Sub-Rule reference
			if (resolved.fieldname === "rule" && actionType === "Sub-Rule") {
				return {
					...resolved,
					label: policyLabel ? __(policyLabel) : resolved.label,
					get_query: () => {
						const parentDocType = store.rule_doc?.document_type;
						const filters = {
							trigger_type: "Callable Event",
							exposed_as_subrule: 1,
							is_active: 1,
							name: ["!=", store.rule_name || ""],
						};
						if (parentDocType) {
							filters.document_type = ["in", [parentDocType, ""]];
						}
						return {
							filters,
						};
					},
				};
			}
			if (policyLabel) {
				resolved = { ...resolved, label: __(policyLabel) };
			}
			return resolved;
		});
});

// Filter visible fields based on depends_on evaluation
const visible_fields = computed(() => {
	const actionType = props.nodeData?.action_type;
	if (!actionType || actionType === "Selector") return [];
	return doc_fields.value.filter((df) => evaluate_depends_on(df.depends_on));
});

// Evaluate depends_on expression
function evaluate_depends_on(expression) {
	if (!expression) return true;

	const doc = props.nodeData;
	if (!doc) return true;

	if (typeof expression === "boolean") {
		return expression;
	}

	if (expression.startsWith("eval:")) {
		try {
			const parent = store.rule_doc;
			return frappe.utils.eval(expression.substr(5), { doc, parent });
		} catch (e) {
			console.warn("Failed to evaluate depends_on:", expression, e);
			return false;
		}
	}

	// Simple fieldname reference
	const value = doc[expression];
	if (Array.isArray(value)) {
		return !!value.length;
	}
	return !!value;
}

// Evaluate mandatory_depends_on
function is_mandatory(df) {
	if (df.reqd) return true;
	if (!df.mandatory_depends_on) return false;
	return evaluate_depends_on(df.mandatory_depends_on);
}

// Evaluate read_only_depends_on
function is_read_only(df) {
	if (props.readOnly) return true;
	if (df.read_only) return true;
	if (!df.read_only_depends_on) return false;
	return evaluate_depends_on(df.read_only_depends_on);
}

// Get field value from node data, normalized for the UI control
function get_normalized_value(df) {
	const val = props.nodeData?.[df.fieldname];
	if (isJsonField(df)) {
		return toCodeString(val);
	}
	return val;
}

// Update field value, normalized for the internal store
function update_normalized_value(df, value) {
	let nextValue = value;
	if (isJsonField(df)) {
		nextValue = fromCodeString(value);
	}
	emit("update:field", df.fieldname, nextValue);
}

// Get options for Autocomplete fields
async function get_autocomplete_options(df) {
	const options_ref = df.options;

	// operation field from canonical contract registry
	if (df.fieldname === "operation") {
		const actionType = normalizeActionType(props.nodeData?.action_type);
		const processName = props.nodeData?.process_name;
		let options = getOperationOptions(actionType, { processName });
		if (actionType === "Process" && !options.length && processName) {
			const operations = await store.get_process_operations(processName);
			options = operations.map((op) => ({
				value: op.func_name,
				label: op.label || op.func_name,
				description: op.description || "",
			}));
		}
		return options.map((op) => ({
			value: op.value || op.func_name,
			label: __(op.label || op.value || op.func_name),
			description: op.description || "",
		}));
	}

	// next_step_if_true / next_step_if_false - get available action nodes
	if (options_ref === "action_id") {
		return get_action_node_options();
	}

	return [];
}

// Get available action nodes for next step selection
function get_action_node_options() {
	const current_id = props.nodeData?.action_id;

	return (store.nodes || [])
		.filter((el) => el.id !== current_id && el.id !== "start")
		.map((el) => ({
			value: el.id,
			label: el.label || el.data?.action_label || el.id,
		}));
}

// Handle button field clicks
function handle_button_click(df) {
	if (df.fieldname === "configure_operation" || df.fieldname === "configures") {
		emit("open:config");
	} else if (df.fieldname === "set_conditions") {
		emit("open:conditions");
	}
}

// Check if field is a button type
function is_button_field(df) {
	return df.fieldtype === "Button";
}

// Check if field needs autocomplete with dynamic options
function needs_autocomplete(df) {
	return (
		df.fieldtype === "Autocomplete" ||
		df.fieldtype === "Link" ||
		df.fieldtype === "Dynamic Link" ||
		df.fieldname === "operation" ||
		df.options === "action_id"
	);
}

const controlRefs = ref([]);
onBeforeUpdate(() => {
	controlRefs.value = [];
});

async function validate() {
	const results = await Promise.all(
		(controlRefs.value || []).map((ref) => {
			if (ref && typeof ref.validate === "function") {
				return ref.validate();
			}
			return { valid: true };
		})
	);
	const errors = results.flatMap((r) => r.errors || []);
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

// Ensure Rule Action meta is loaded
onMounted(async () => {
	if (!frappe.get_meta("Rule Action")) {
		await frappe.model.with_doctype("Rule Action");
	}
});
</script>

<template>
	<div class="action-field-properties">
		<div v-for="df in visible_fields" :key="df.fieldname" class="field-wrapper">
			<!-- Button fields (configures, set_conditions) -->
			<template v-if="is_button_field(df)">
				<button class="btn btn-default btn-sm w-100" @click="handle_button_click(df)">
					<i
						v-if="
							df.fieldname === 'configure_operation' || df.fieldname === 'configures'
						"
						class="fa fa-cog"
					></i>
					<i v-else-if="df.fieldname === 'set_conditions'" class="fa fa-code-fork"></i>
					{{ __(df.label) }}
				</button>
			</template>

			<!-- Autocomplete / Link / Dynamic Link fields -->
			<template v-else-if="needs_autocomplete(df)">
				<ComboBoxControl
					ref="controlRefs"
					:df="{
						...df,
						reqd: is_mandatory(df),
						read_only: is_read_only(df),
					}"
					:modelValue="get_normalized_value(df)"
					:doctype="
						df.fieldtype === 'Dynamic Link'
							? nodeData?.[df.options] || ''
							: df.options || df.target_doctype
					"
					:get_query="(txt) => get_autocomplete_options(df)"
					:doc="nodeData"
					:read_only="is_read_only(df)"
					:showValidation="showValidation"
					@update:modelValue="update_normalized_value(df, $event)"
				/>
			</template>

			<template v-else>
				<ControlFactory
					ref="controlRefs"
					:df="{
						...df,
						reqd: is_mandatory(df),
						read_only: is_read_only(df),
					}"
					:modelValue="get_normalized_value(df)"
					:read_only="is_read_only(df)"
					:showValidation="showValidation"
					:doc="nodeData"
					@update:modelValue="update_normalized_value(df, $event)"
				/>
			</template>
		</div>
	</div>
</template>

<style scoped>
.action-field-properties {
	display: flex;
	flex-direction: column;
}

.field-wrapper {
	margin-bottom: 12px;
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
</style>
