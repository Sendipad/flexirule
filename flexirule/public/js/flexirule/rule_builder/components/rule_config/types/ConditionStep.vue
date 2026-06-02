<template>
	<div class="condition-step">
		<div class="fxr-card mb-4">
			<div class="fxr-card-body d-flex align-items-center justify-content-between">
				<div class="d-flex align-items-center gap-3">
					<div class="header-icon-box">
						<i class="fa fa-code-fork"></i>
					</div>
					<div class="d-flex flex-column">
						<h5 class="mb-0 fw-bold">{{ __("Execution Conditions") }}</h5>
						<p class="text-muted extra-small mb-0">
							{{
								__(
									"Define logic rules to determine if and how this action should execute."
								)
							}}
						</p>
					</div>
				</div>
				<div class="header-actions">
					<label class="d-flex align-items-center gap-2 mb-0" style="cursor: pointer">
						<input type="checkbox" v-model="showOldDoc" class="fxr-checkbox-input" />
						<span class="small text-muted">{{ __("Show Old Doc Fields") }}</span>
					</label>
				</div>
			</div>
		</div>

		<div class="condition-builder-container">
			<ConditionBuilder
				:modelValue="localConditions"
				:docFields="docFields"
				:variableOptions="combinedVariableOptions"
				@update:modelValue="updateConditions"
			/>
		</div>

		<div v-if="localConditions.conditions?.length" class="condition-step-footer mt-4">
			<div class="info-alert">
				<i class="fa fa-info-circle"></i>
				<span>{{
					__("Conditions will be evaluated at runtime to determine the next step.")
				}}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "../../../stores";
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import { validateConditions } from "../../condition_builder/condition_validator.js";
import { getConditionPayload } from "../../../utils/condition_payload";

const props = defineProps({
	node: Object,
});

const store = useStore();
const localConditions = ref({ op: "and", conditions: [] });
const showOldDoc = ref(false);
const variableFields = ref([]);

function hydrate(tree) {
	if (!tree || typeof tree !== "object") return tree;
	const hydrated = Array.isArray(tree) ? [...tree] : { ...tree };

	if (!hydrated.id) {
		hydrated.id = frappe.utils.get_random(12);
	}

	if (hydrated.conditions && Array.isArray(hydrated.conditions)) {
		hydrated.conditions = hydrated.conditions.map((c) => hydrate(c));
	}

	if (hydrated.where) {
		hydrated.where = hydrate(hydrated.where);
	}

	return hydrated;
}

function dehydrate(tree) {
	if (!tree || typeof tree !== "object") return tree;
	const clean = Array.isArray(tree) ? [...tree] : { ...tree };

	if (clean.id) delete clean.id;

	if (clean.conditions && Array.isArray(clean.conditions)) {
		clean.conditions = clean.conditions.map((c) => dehydrate(c));
	}

	if (clean.where) {
		clean.where = dehydrate(clean.where);
	}

	return clean;
}

watch(
	() => {
		if (props.node?.type === "start") {
			return props.node?.data?.trigger_condition;
		}
		return getConditionPayload({
			config: props.node?.data?.config,
			condition_json: props.node?.data?.condition_json,
		});
	},
	(val) => {
		if (val) {
			try {
				const parsed = typeof val === "string" ? JSON.parse(val) : val;

				const currentClean = dehydrate(localConditions.value);
				if (JSON.stringify(parsed) === JSON.stringify(currentClean)) {
					return;
				}

				localConditions.value = hydrate(parsed);
			} catch (e) {
				localConditions.value = {
					id: frappe.utils.get_random(12),
					op: "and",
					conditions: [],
				};
			}
		} else {
			localConditions.value = { id: frappe.utils.get_random(12), op: "and", conditions: [] };
		}
	},
	{ immediate: true }
);

function updateConditions(val) {
	localConditions.value = val;
	save();
}

function save() {
	if (!props.node?.data) return;

	const clean = dehydrate(localConditions.value);

	if (props.node.type === "start") {
		props.node.data.trigger_condition = clean;
	} else {
		props.node.data.config = clean;
		props.node.data.condition_json = null;
	}
}

const docFields = computed(() => {
	const dedupe = new Map();
	const pushField = (field) => {
		if (!field?.value) return;
		dedupe.set(field.value, field);
	};

	store.doc_fields.forEach(pushField);
	variableFields.value.forEach(pushField);
	let fields = Array.from(dedupe.values());

	if (showOldDoc.value) {
		const metaStore = store;
		const doctype = store.rule_doc?.document_type;
		if (doctype) {
			const oldFields = metaStore.get_fields_for_doctype(doctype, {
				alias: "old_doc",
				valueMode: "expression",
			});
			fields = [...fields, ...oldFields];
		}
	}

	const triggerTypeOptions = "DocType Event\nScheduler Event\nCallable Event";
	const triggerEventOptions = (store.trigger_event_options || []).join("\n");
	const contextFields = [
		{
			label: "context.doctype (Current Doctype)",
			value: "doctype",
			fieldname: "doctype",
			fieldtype: "Link",
			options: "DocType",
			operators: [
				"==",
				"!=",
				"in",
				"not in",
				"is_set",
				"is_not_set",
				"is_submittable",
				"has_field",
			],
			is_context: true,
		},
		{
			label: "caller.trigger_type (Caller Trigger Type)",
			value: "caller.trigger_type",
			fieldname: "caller_trigger_type",
			fieldtype: "Select",
			options: triggerTypeOptions,
			is_context: true,
		},
		{
			label: "caller.trigger_event (Caller Trigger Event)",
			value: "caller.trigger_event",
			fieldname: "caller_trigger_event",
			fieldtype: "Select",
			options: triggerEventOptions,
			is_context: true,
		},
		{
			label: "caller.document_type (Caller DocType)",
			value: "caller.document_type",
			fieldname: "caller_document_type",
			fieldtype: "Link",
			options: "DocType",
			operators: [
				"==",
				"!=",
				"in",
				"not in",
				"is_set",
				"is_not_set",
				"is_submittable",
				"has_field",
			],
			is_context: true,
		},
		{
			label: "rule.trigger_type (Target Trigger Type)",
			value: "rule.trigger_type",
			fieldname: "rule_trigger_type",
			fieldtype: "Select",
			options: triggerTypeOptions,
			is_context: true,
		},
		{
			label: "rule.trigger_event (Target Trigger Event)",
			value: "rule.trigger_event",
			fieldname: "rule_trigger_event",
			fieldtype: "Select",
			options: triggerEventOptions,
			is_context: true,
		},
		{
			label: "rule.document_type (Target DocType)",
			value: "rule.document_type",
			fieldname: "rule_document_type",
			fieldtype: "Link",
			options: "DocType",
			operators: [
				"==",
				"!=",
				"in",
				"not in",
				"is_set",
				"is_not_set",
				"is_submittable",
				"has_field",
			],
			is_context: true,
		},
	];
	fields = [...fields, ...contextFields];

	return fields.sort((a, b) => a.label.localeCompare(b.label));
});

const combinedVariableOptions = computed(() => {
	const dedupe = new Map();
	const pushOption = (v) => {
		const key = v.value || v;
		if (!key) return;
		dedupe.set(key, v);
	};

	docFields.value.forEach(pushOption);
	variableFields.value.forEach(pushOption);

	return Array.from(dedupe.values());
});

async function refreshVariableFields() {
	const nodeId = props.node?.id;
	if (!nodeId || props.node?.type === "start") {
		variableFields.value = [];
		return;
	}

	try {
		const available = await store.getAvailableVariables(nodeId);
		variableFields.value = available || [];
	} catch (e) {
		variableFields.value = [];
	}
}

onMounted(async () => {
	const node = props.node;
	if (!node) return;

	const doctype = node.data?.document_type || store.rule_doc?.document_type;
	if (doctype && !store.doc_fields.length) {
		await store.fetch_metadata(doctype);
	}
	await refreshVariableFields();
});

watch(
	() => [
		props.node?.id,
		(store.nodes || [])
			.filter(Boolean)
			.map((node) => [
				node.id,
				node.data?.return_variable,
				node.data?.return_type,
				node.data?.resolved_output_schema,
			]),
	],
	() => {
		refreshVariableFields();
	},
	{ deep: true }
);

function validate() {
	const type = props.node?.data?.action_type || props.node?.type;
	const isMandatory = type === "Condition";
	const result = validateConditions(localConditions.value, true, isMandatory);
	if (!result.valid) {
		return { valid: false, errors: [result.message] };
	}
	return { valid: true, errors: [] };
}

defineExpose({
	validate,
});
</script>

<style scoped>
.condition-step {
	display: flex;
	flex-direction: column;
}

.header-icon-box {
	width: 36px;
	height: 36px;
	background: var(--fr-primary-subtle);
	color: var(--fr-primary);
	border-radius: var(--fr-radius-md);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 16px;
}

.extra-small {
	font-size: 11px;
}

.condition-builder-container {
	position: relative;
	z-index: 10;
}

.condition-builder-container :deep(.condition-builder) {
	padding: 0;
	background: transparent;
}

.info-alert {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	padding: 12px 16px;
	background: #eff6ff;
	border: 1px solid #bfdbfe;
	color: #1e40af;
	border-radius: var(--fr-radius-lg);
	font-size: 13px;
	line-height: 1.4;
}

.info-alert i {
	margin-top: 2px;
	font-size: 16px;
}

.fxr-checkbox-input {
	accent-color: var(--fr-primary);
}
</style>
