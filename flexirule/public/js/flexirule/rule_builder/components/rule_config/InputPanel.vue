<template>
	<div class="input-panel" :class="mode">
		<div class="panel-header" v-if="mode === 'config' && !store.use_modern_layout">
			<h4>{{ __("Setup & Input") }}</h4>
			<p class="text-muted small">{{ __("Define reference and operation") }}</p>
		</div>

		<div class="panel-sections">
			<!-- Configuration Section (Only for 'config' mode) -->
			<div v-if="mode === 'config'" class="panel-section setup-section">
				<div class="setup-controls">
					<ControlFactory
						v-if="showProcessName"
						:df="processNameField"
						:modelValue="node.data?.process_name"
						:read_only="readOnly"
						@update:modelValue="updateField('process_name', $event)"
					/>

					<ControlFactory
						v-if="showOperation"
						:df="dynamicOperationField"
						:modelValue="node.data?.operation"
						:read_only="readOnly"
						@update:modelValue="updateField('operation', $event)"
					/>

					<!-- Core Identity Fields -->
					<ControlFactory
						v-if="showReferenceDoctype"
						:df="referenceDoctypeField"
						:modelValue="node.data?.reference_doctype"
						:read_only="readOnly"
						@update:modelValue="updateField('reference_doctype', $event)"
					/>

					<ControlFactory
						v-if="showRuleField"
						:df="ruleField"
						:modelValue="node.data?.rule"
						:read_only="readOnly"
						@update:modelValue="updateField('rule', $event)"
					/>

					<!-- Secondary Setup -->
					<ControlFactory
						v-if="showReferenceDocname"
						:df="referenceDocnameField"
						:modelValue="node.data?.reference_docname"
						:read_only="readOnly"
						@update:modelValue="updateField('reference_docname', $event)"
					/>

					<ControlFactory
						v-if="showInputSource"
						:df="inputSourceField"
						:modelValue="node.data?.input_source"
						:read_only="readOnly"
						@update:modelValue="updateField('input_source', $event)"
					/>
				</div>
			</div>

			<!-- Available Variables (Always shown in 'variables' mode, optional in 'config') -->
			<div class="panel-section variables-section">
				<div class="section-header">
					<h5 class="section-title">
						{{
							mode === "variables"
								? __("Available Variables")
								: __("Context Variables")
						}}
					</h5>
					<button class="btn btn-xs btn-link" @click="refreshVariables">
						<i class="fa fa-refresh"></i>
					</button>
				</div>
				<div class="variable-search mb-2">
					<div class="input-group input-group-sm">
						<div class="input-group-prepend">
							<span class="input-group-text"><i class="fa fa-search"></i></span>
						</div>
						<input
							type="text"
							class="form-control"
							v-model="searchQuery"
							:placeholder="__('Search variables...')"
						/>
					</div>
				</div>

				<div class="variable-list v2-scrollbar">
					<div v-if="loading" class="text-center p-3">
						<div class="spinner-border spinner-border-sm text-muted"></div>
					</div>
					<template v-else>
						<div
							v-for="v in filteredVariables"
							:key="v.value"
							class="variable-item"
							:title="v.label"
							draggable="true"
							@dragstart="onDragStart($event, v)"
						>
							<div class="variable-info">
								<span class="variable-label">{{ v.label }}</span>
								<span class="variable-type">{{ v.type || "Data" }}</span>
							</div>
							<button
								class="btn btn-xs btn-link text-muted opacity-20 hover-opacity-100"
								@click="copyToClipboard(`{{ ${v.value} }}`)"
							>
								<i class="fa fa-copy"></i>
							</button>
						</div>
						<div v-if="filteredVariables.length === 0" class="empty-state">
							{{
								searchQuery
									? __("No matching variables")
									: __("No scope variables available")
							}}
						</div>
					</template>
				</div>
			</div>

			<!-- DocType Fields (Only in 'config' mode when a DocType is selected) -->
			<div
				v-if="mode === 'config' && node.data?.reference_doctype"
				class="panel-section doctype-fields-section"
			>
				<h5 class="section-title">
					{{ __("{0} Fields").replace("{0}", node.data.reference_doctype) }}
				</h5>
				<div class="variable-list v2-scrollbar mt-2">
					<div v-if="loadingFields" class="text-center p-2">
						<div class="spinner-border spinner-border-sm text-muted"></div>
					</div>
					<template v-else>
						<div
							v-for="f in doctypeFields"
							:key="f.fieldname"
							class="variable-item field-item"
							:title="f.label"
							draggable="true"
							@dragstart="onDragStart($event, f, true)"
						>
							<span class="variable-label">{{ f.label }}</span>
							<span class="variable-type">{{ f.fieldtype }}</span>
						</div>
					</template>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "../../store";
import {
	getContract,
	getFieldLabel,
	getOperationOptions,
	getEffectiveActionPolicy,
} from "../../../core/contracts.js";
import ControlFactory from "../../controls/ControlFactory.vue";
import SubRuleNodeConfig from "../node_configs/SubRuleNodeConfig.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
	mode: { type: String, default: "config" }, // 'config' or 'variables'
});

const store = useStore();
const variables = ref([]);
const doctypeFields = ref([]);
const loading = ref(false);
const loadingFields = ref(false);
const searchQuery = ref("");

const contract = computed(() => {
	const type = props.node?.data?.action_type || props.node?.type;
	return type ? getContract(type) : null;
});

const showReferenceDoctype = computed(() => {
	if (!contract.value) return false;
	const fields = contract.value.required_fields || [];
	const isQueryReport =
		props.node.data?.action_type === "Query Records" &&
		props.node.data?.operation === "Query Report";

	return (
		!isQueryReport &&
		(fields.includes("reference_doctype") ||
			["Process", "Set Value"].includes(props.node.data?.action_type))
	);
});

const showProcessName = computed(() => {
	return props.node.data?.action_type === "Process";
});

const showRuleField = computed(() => {
	return props.node.data?.action_type === "Sub-Rule";
});

const showOperation = computed(() => {
	if (!contract.value) return false;
	const type = props.node.data?.action_type;
	if (!type) return false;
	return (
		getOperationOptions(type, { processName: props.node.data?.process_name }).length > 0 ||
		["Process", "Query Records", "Document Action"].includes(type)
	);
});

const showReferenceDocname = computed(() => {
	const type = props.node.data?.action_type;
	const op = props.node.data?.operation;

	if (type === "Query Records") {
		return ["Query Doc", "Query Report"].includes(op);
	}
	if (type === "Document Action") {
		return ["Update Existing", "Delete Record"].includes(op);
	}
	if (type === "Process" && op?.includes("Doc")) return true;

	return false;
});

const showInputSource = computed(() => {
	if (!contract.value) return false;
	return ["Query Records", "Document Action"].includes(props.node.data?.action_type);
});

const forcedReferenceDoctype = computed(() => {
	if (props.node.data?.action_type !== "Document Action") return null;
	if (props.node.data?.operation === "Add Comment") return "Comment";
	if (props.node.data?.operation === "Create ToDo") return "ToDo";
	return null;
});

// -- Field Definitions --
const referenceDoctypeField = computed(() => {
	let description = __("Target DocType for this action.");
	if (props.node.data?.action_type === "Document Action" && forcedReferenceDoctype.value) {
		description = __("{0} mode always targets the {1} DocType.")
			.replace("{0}", props.node.data.operation)
			.replace("{1}", forcedReferenceDoctype.value);
	}

	return {
		fieldname: "reference_doctype",
		fieldtype: "Link",
		label:
			getFieldLabel(props.node.data?.action_type, "reference_doctype") ||
			__("Reference DocType"),
		options: "DocType",
		reqd: 1,
		read_only: Boolean(forcedReferenceDoctype.value),
		description,
	};
});

const processNameField = {
	fieldname: "process_name",
	fieldtype: "Link",
	label: __("Process"),
	options: "Process",
	reqd: 1,
};

const ruleField = {
	fieldname: "rule",
	fieldtype: "Link",
	label: __("Sub-Rule"),
	options: "Rule",
	reqd: 1,
	get_query: () => {
		const parentDocType = store.rule_doc?.document_type;
		return {
			filters: {
				trigger_type: "Callable Event",
				exposed_as_subrule: 1,
				is_active: 1,
				document_type: ["in", parentDocType ? [parentDocType, ""] : [""]],
				name: ["!=", store.rule_name || ""],
			},
		};
	},
};

const referenceDocnameField = computed(() => {
	const actionType = props.node?.data?.action_type;
	const operation = props.node?.data?.operation;
	const refDocType = props.node?.data?.reference_doctype;

	// Special case: Query Report
	if (actionType === "Query Records" && operation === "Query Report") {
		return {
			fieldname: "reference_docname",
			fieldtype: "Link",
			label: __("Report Name"),
			options: "Report",
			reqd: 1,
			description: __("Select the report to run."),
		};
	}

	// Dynamic Link for Query Doc or Document Actions
	const isLinkNeeded =
		(actionType === "Query Records" && operation === "Query Doc") ||
		(actionType === "Document Action" &&
			["Update Existing", "Delete Record"].includes(operation));

	if (isLinkNeeded && refDocType && refDocType !== "Report") {
		return {
			fieldname: "reference_docname",
			fieldtype: "Link",
			label: __("Reference Name"),
			options: refDocType,
			reqd: 1,
			description: __("Select the {0} record.").replace("{0}", refDocType),
		};
	}

	return {
		fieldname: "reference_docname",
		fieldtype: "Data",
		label: __("Reference Name"),
		description: __("The document name, ID, or an expression."),
	};
});

const inputSourceField = {
	fieldname: "input_source",
	fieldtype: "Select",
	label: __("Input Source"),
	options: "Context Doc\nContext Variable\nBoth",
};

const dynamicOperationField = computed(() => {
	const actionType = props.node.data?.action_type;
	const options = getOperationOptions(actionType, {
		processName: props.node.data?.process_name,
	});
	const label =
		getFieldLabel(actionType, "operation", {
			operation: props.node.data?.operation,
			processName: props.node.data?.process_name,
		}) ||
		contract.value?.operation_label ||
		__("Operation / Mode");

	return {
		fieldname: "operation",
		fieldtype: options.length ? "Select" : "Autocomplete",
		label: label,
		options: options.map((opt) => opt.value).join("\n"),
		reqd: 1,
		get_options: async () => {
			if (actionType === "Process" && !options.length && props.node.data?.process_name) {
				const ops = await store.get_process_operations(props.node.data.process_name);
				return ops.map((o) => ({
					label: __(o.label || o.func_name),
					value: o.func_name,
					description: "",
				}));
			}
			return options.map((opt) => ({
				label: __(opt.label || opt.value),
				value: opt.value,
				description: opt.process_name ? `${opt.process_name}` : "",
			}));
		},
	};
});

const filteredVariables = computed(() => {
	if (!searchQuery.value) return variables.value;
	const q = searchQuery.value.toLowerCase();
	return variables.value.filter(
		(v) => v.label.toLowerCase().includes(q) || v.value.toLowerCase().includes(q)
	);
});

function onDragStart(event, item, isField = false) {
	if (event.dataTransfer) {
		const text = isField ? `{{ doc.${item.fieldname} }}` : `{{ ${item.value} }}`;
		event.dataTransfer.setData("text/plain", text);
		event.dataTransfer.setData(
			"application/x-flexirule-variable",
			isField ? `doc.${item.fieldname}` : item.value
		);
		event.dataTransfer.effectAllowed = "copy";
	}
}

async function refreshVariables() {
	if (!props.node?.id) return;
	loading.value = true;
	try {
		variables.value = await store.getAvailableVariables(props.node.id);
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
}

async function loadDoctypeFields() {
	const dt = props.node?.data?.reference_doctype;
	if (!dt) {
		doctypeFields.value = [];
		return;
	}
	loadingFields.value = true;
	try {
		doctypeFields.value = await flexirule.utils.get_doctype_fields(dt);
	} catch (e) {
		doctypeFields.value = [];
	} finally {
		loadingFields.value = false;
	}
}

function updateField(fieldname, value) {
	if (props.node?.data) {
		if (fieldname === "operation") {
			const actionType = props.node.data?.action_type;

			// Handle Document Action special modes
			if (actionType === "Document Action") {
				const isSpecialCreateDocsMode = ["Add Comment", "Create ToDo"].includes(value);
				if (value === "Add Comment") {
					props.node.data.reference_doctype = "Comment";
					props.node.data.reference_docname = null;
				} else if (value === "Create ToDo") {
					props.node.data.reference_doctype = "ToDo";
					props.node.data.reference_docname = null;
				} else if (
					["Comment", "ToDo"].includes(props.node.data.reference_doctype) &&
					["Create New", "Update Existing"].includes(value)
				) {
					props.node.data.reference_doctype = null;
					props.node.data.reference_docname = null;
				}

				if (isSpecialCreateDocsMode) {
					// These modes act on the current context document
					props.node.data.mutation_mode = null;
					props.node.data.return_variable = null;
					props.node.data.return_type = null;
					props.node.data.resolved_output_schema = null;
					clearConfigKey("output_mapping");
				}
			}

			// Handle Query Records -> Query Report special mode
			if (actionType === "Query Records" && value === "Query Report") {
				props.node.data.reference_doctype = "Report";
				props.node.data.reference_docname = null;
			} else if (
				actionType === "Query Records" &&
				props.node.data.reference_doctype === "Report"
			) {
				// Switching away from report mode should restore an editable doctype context.
				props.node.data.reference_doctype = store.rule_doc?.document_type || null;
			}

			if (actionType === "Process" && !props.node.data.process_name && value) {
				const matches = getOperationOptions("Process", {})
					.filter((op) => op.value === value && op.process_name)
					.map((op) => op.process_name);
				const unique = [...new Set(matches)];
				if (unique.length === 1) {
					props.node.data.process_name = unique[0];
				}
			}

			const policy = getEffectiveActionPolicy(actionType, {
				operation: value,
				processName: props.node.data?.process_name,
			});
			const allowedMutations = policy.allowed_mutations || [];
			const allowedReturnTypes = policy.allowed_return_types || [];
			if (
				props.node.data.mutation_mode &&
				allowedMutations.length &&
				!allowedMutations.includes(props.node.data.mutation_mode)
			) {
				props.node.data.mutation_mode = null;
			}
			if (
				props.node.data.return_type &&
				allowedReturnTypes.length &&
				!allowedReturnTypes.includes(props.node.data.return_type)
			) {
				props.node.data.return_type = null;
			}
			if (!props.node.data.return_type && policy.default_return_type) {
				props.node.data.return_type = policy.default_return_type;
			}
		}

		if (
			fieldname === "reference_doctype" &&
			forcedReferenceDoctype.value &&
			value !== forcedReferenceDoctype.value
		) {
			props.node.data.reference_doctype = forcedReferenceDoctype.value;
			store.mark_dirty();
			return;
		}

		props.node.data[fieldname] = value;
		store.mark_dirty();
	}
}

function ensureActionDefaults() {
	if (!props.node?.data) return;
	const actionType = props.node.data.action_type;
	const currentRuleDoctype = store.rule_doc?.document_type || "";

	if (actionType === "Query Records") {
		if (!props.node.data.operation) {
			props.node.data.operation = "Query List";
			store.mark_dirty();
		}
		if (props.node.data.operation === "Query Report") {
			if (props.node.data.reference_doctype !== "Report") {
				props.node.data.reference_doctype = "Report";
				store.mark_dirty();
			}
		} else if (!props.node.data.reference_doctype && currentRuleDoctype) {
			props.node.data.reference_doctype = currentRuleDoctype;
			store.mark_dirty();
		}
	}

	if (
		actionType === "Document Action" &&
		!forcedReferenceDoctype.value &&
		!props.node.data.reference_doctype &&
		currentRuleDoctype
	) {
		props.node.data.reference_doctype = currentRuleDoctype;
		store.mark_dirty();
	}
}

watch(
	() => props.node?.data?.process_name,
	(processName) => {
		const actionType = props.node?.data?.action_type;
		if (actionType !== "Process" || !props.node?.data) return;
		const opOptions = getOperationOptions(actionType, { processName }).map((opt) => opt.value);
		if (props.node.data.operation && !opOptions.includes(props.node.data.operation)) {
			props.node.data.operation = null;
			store.mark_dirty();
		}
	}
);

function clearConfigKey(key) {
	if (!props.node?.data) return;
	let currentConfig = {};
	if (props.node.data.config && typeof props.node.data.config === "object") {
		currentConfig = { ...props.node.data.config };
	} else if (typeof props.node.data.config === "string") {
		try {
			currentConfig = JSON.parse(props.node.data.config) || {};
		} catch (e) {
			currentConfig = {};
		}
	}
	delete currentConfig[key];
	props.node.data.config = currentConfig;
}

watch(
	() => forcedReferenceDoctype.value,
	(value) => {
		if (!props.node?.data || !value) return;
		if (props.node.data.reference_doctype !== value) {
			props.node.data.reference_doctype = value;
			store.mark_dirty();
		}
	}
);

watch(
	() => props.node?.data?.reference_doctype,
	() => loadDoctypeFields(),
	{ immediate: true }
);

watch(
	() => props.node?.id,
	() => refreshVariables(),
	{ immediate: true }
);

watch(
	() => [
		props.node?.data?.action_type,
		props.node?.data?.operation,
		store.rule_doc?.document_type,
	],
	() => ensureActionDefaults(),
	{ immediate: true }
);

onMounted(() => {
	refreshVariables();
});

function copyToClipboard(text) {
	if (frappe.utils.copy_to_clipboard) {
		frappe.utils.copy_to_clipboard(text);
	} else {
		const el = document.createElement("textarea");
		el.value = text;
		document.body.appendChild(el);
		el.select();
		document.execCommand("copy");
		document.body.removeChild(el);
		frappe.show_alert({
			message: __("Copied to clipboard: {0}").replace("{0}", text),
			indicator: "blue",
		});
	}
}

defineExpose({
	validate: () => {
		const errors = [];
		if (props.node?.data?.action_type === "Document Action") {
			if (
				props.node.data.operation === "Add Comment" &&
				props.node.data.reference_doctype !== "Comment"
			) {
				errors.push(__("Add Comment mode requires Reference DocType = Comment"));
			}
			if (
				props.node.data.operation === "Create ToDo" &&
				props.node.data.reference_doctype !== "ToDo"
			) {
				errors.push(__("Create ToDo mode requires Reference DocType = ToDo"));
			}
		}
		return { valid: errors.length === 0, errors };
	},
});
</script>

<style scoped>
.input-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: #f8fafc;
}

.panel-header {
	padding: 20px;
	border-bottom: 1px solid var(--border-color);
	background: #fff;
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 15px;
	font-weight: 600;
}

.panel-sections {
	flex: 1;
	overflow-y: auto;
	padding: 20px;
	display: flex;
	flex-direction: column;
	gap: 24px;
}

.panel-section {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.section-title {
	margin: 0;
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: #64748b;
}

.section-divider {
	height: 1px;
	background: #e2e8f0;
	margin: 4px 0;
}

.variable-list {
	display: flex;
	flex-direction: column;
	gap: 6px;
	max-height: 350px;
	overflow-y: auto;
	padding-right: 4px;
}

.variable-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 12px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	font-size: 11px;
	cursor: grab;
	transition: all 0.2s;
}

.variable-item:hover {
	border-color: var(--primary);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	transform: translateX(2px);
}

.variable-label {
	font-weight: 600;
	color: #1e293b;
}

.variable-type {
	font-size: 9px;
	padding: 2px 6px;
	background: #f1f5f9;
	border-radius: 4px;
	color: #64748b;
}

.guide-content {
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 12px;
}

.guide-icon-small {
	width: 24px;
	height: 24px;
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #fff;
	font-size: 12px;
}

.guide-text-small {
	font-size: 12px;
	line-height: 1.5;
	color: #475569;
	margin: 0;
}

.insight-label {
	font-size: 10px;
	font-weight: 700;
	color: var(--primary);
	text-transform: uppercase;
	display: block;
	margin-bottom: 4px;
}

.insight-text {
	font-size: 11px;
	color: #64748b;
	background: #f0f9ff;
	padding: 8px;
	border-radius: 8px;
	border-left: 3px solid var(--primary);
	margin: 0;
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}
.v2-scrollbar::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 10px;
}

.empty-state {
	padding: 20px;
	text-align: center;
	color: #94a3b8;
	font-size: 11px;
	background: #f8fafc;
	border: 1px dashed #e2e8f0;
	border-radius: 8px;
}
</style>
