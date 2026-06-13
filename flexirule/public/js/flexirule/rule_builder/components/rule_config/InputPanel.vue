<template>
	<div class="input-panel fxr-accent-scope" :class="mode" :style="panelStyleVars">
		<div class="panel-header" v-if="mode === 'config' && !store.use_modern_layout">
			<h4>{{ __("Setup & Input") }}</h4>
			<p class="text-muted small">{{ __("Define reference and operation") }}</p>
		</div>

		<div class="panel-sections v2-scrollbar">
			<!-- SETTINGS SECTION -->
			<div v-if="mode === 'config'" class="panel-section setup-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Setup & Input") }}</h5>
				</div>
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

			<!-- DATA SECTION (Context Variables) -->
			<div class="data-tab-content">
				<!-- Context Variables -->
				<div class="panel-section variables-section">
					<div class="section-header">
						<h5 class="section-title">
							{{
								mode === "variables"
									? __("Available Variables")
									: __("Context Variables")
							}}
						</h5>
						<div class="section-actions">
							<button
								class="btn btn-xs btn-link"
								@click="variablesCollapsed = !variablesCollapsed"
								:title="
									variablesCollapsed
										? __('Expand Context Variables')
										: __('Collapse Context Variables')
								"
							>
								<i
									class="fa"
									:class="
										variablesCollapsed ? 'fa-chevron-down' : 'fa-chevron-up'
									"
								></i>
							</button>
							<button
								v-if="!variablesCollapsed"
								class="btn btn-xs btn-link"
								@click="refreshVariables"
							>
								<i class="fa fa-refresh"></i>
							</button>
						</div>
					</div>
					<div v-if="!variablesCollapsed" class="variable-search mb-2">
						<div class="input-group input-group-sm">
							<div class="input-group-prepend">
								<span class="input-group-text"><i class="fa fa-search"></i></span>
							</div>
							<input
								ref="variableSearchRef"
								type="text"
								class="form-control"
								v-model="searchQuery"
								:placeholder="__('Search variables...')"
							/>
						</div>
					</div>

					<div v-if="!variablesCollapsed" class="variable-list v2-scrollbar">
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
								tabindex="0"
								@dragstart="onDragStart($event, v)"
								@click="insertOrCopy(v.value)"
								@keydown.enter.prevent="insertOrCopy(v.value)"
								@keydown.c.prevent="copyToClipboard(`{{ ${v.value} }}`)"
								@keydown.down.prevent="focusSibling($event, 1)"
								@keydown.up.prevent="focusSibling($event, -1)"
							>
								<div class="variable-info">
									<span class="variable-label">{{ v.label }}</span>
									<span class="variable-type">{{ v.type || "Data" }}</span>
								</div>
								<button
									class="btn btn-xs btn-link text-muted opacity-20 hover-opacity-100"
									tabindex="-1"
									@click.stop="copyToClipboard(`{{ ${v.value} }}`)"
									:title="__('Copy to clipboard')"
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
					<div v-else class="section-collapsed-note">
						{{ __("Context variables are collapsed.") }}
					</div>
				</div>

				<!-- Document Data Tree -->
				<div
					v-show="activeTab === 'data' && doctypeContext"
					class="panel-section doctype-fields-section mt-4"
				>
					<h5 class="section-title mb-2">
						{{ __("Document Data") }}
					</h5>

					<div class="variable-search mb-2">
						<div class="input-group input-group-sm">
							<div class="input-group-prepend">
								<span class="input-group-text"><i class="fa fa-search"></i></span>
							</div>
							<input
								type="text"
								class="form-control"
								v-model="fieldSearchQuery"
								:placeholder="__('Search fields...')"
							/>
						</div>
					</div>

					<div class="variable-list v2-scrollbar mt-2">
						<div v-if="loadingFields" class="text-center p-2">
							<div class="spinner-border spinner-border-sm text-muted"></div>
						</div>
						<template v-else>
							<div class="tree-container">
								<div
									v-for="(group, groupName) in groupedFields"
									:key="groupName"
									class="tree-group"
								>
									<!-- Group Header (Table Name or 'doc') -->
									<div class="tree-group-header" @click="toggleGroup(groupName)">
										<i
											class="fa fa-fw"
											:class="
												expandedGroups[groupName]
													? 'fa-chevron-down'
													: 'fa-chevron-right'
											"
										></i>
										<span class="tree-group-title">
											{{ groupName === doctypeContext ? "doc" : groupName }}
										</span>
									</div>

									<!-- Group Items -->
									<div
										v-show="expandedGroups[groupName]"
										class="tree-group-items"
									>
										<div
											v-for="f in group.fields"
											:key="f.fieldname"
											class="tree-item"
											:title="f.label"
											draggable="true"
											tabindex="0"
											@dragstart="onDragStart($event, f, true, groupName)"
											@click="insertOrCopy(buildFieldPath(f, groupName))"
											@keydown.enter.prevent="
												insertOrCopy(buildFieldPath(f, groupName))
											"
											@keydown.down.prevent="focusSibling($event, 1)"
											@keydown.up.prevent="focusSibling($event, -1)"
										>
											<span class="tree-item-label">{{ f.fieldname }}</span>
											<span class="tree-item-type">({{ f.fieldtype }})</span>
										</div>
									</div>
								</div>
							</div>
						</template>
					</div>

					<div class="tips-box mt-4">
						<h6><i class="fa fa-info-circle text-primary"></i> {{ __("Tips") }}</h6>
						<ul>
							<li>{{ __("Drag & drop to insert") }}</li>
						</ul>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from "vue";
import { useStore } from "../../stores";
import { insertIntoActiveTGC } from "../../utils/tgc_focus";
import { copyText } from "../../../utils/clipboard";

const variableSearchRef = ref(null);

function focusSibling(e, direction) {
	const el = e.target;
	const sibling = direction > 0 ? el.nextElementSibling : el.previousElementSibling;
	if (
		sibling &&
		(sibling.classList.contains("variable-item") || sibling.classList.contains("tree-item"))
	) {
		sibling.focus();
	}
}

function focusSearch() {
	if (variablesCollapsed.value) {
		variablesCollapsed.value = false;
	}
	nextTick(() => {
		variableSearchRef.value?.focus();
	});
}

defineExpose({
	focusSearch,
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
import {
	applyOutputPolicyDefaults,
	getContract,
	getDerivedFieldState,
	getFieldLabel,
	getOperationOptions,
	getEffectiveActionPolicy,
	normalizeActionType,
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
const fieldSearchQuery = ref("");
const variablesCollapsed = ref(false);
const expandedGroups = ref({});

const contract = computed(() => {
	const type = normalizeActionType(props.node?.data?.action_type || props.node?.type);
	return type ? getContract(type) : null;
});

const panelStyleVars = computed(() => {
	const accent = contract.value?.css?.color || "var(--fxr-accent)";
	return {
		"--fxr-node-accent": accent,
		"--fxr-node-accent-light": `color-mix(in srgb, ${accent} 12%, var(--fxr-surface))`,
	};
});

const currentActionType = computed(() =>
	normalizeActionType(props.node?.data?.action_type || props.node?.type)
);

const showReferenceDoctype = computed(() => {
	if (!contract.value) return false;
	const actionType = props.node.data?.action_type;
	const fallback = (contract.value.required_fields || []).includes("reference_doctype");
	const state = getDerivedFieldState(
		actionType,
		"reference_doctype",
		props.node?.data || {},
		store.rule_doc || {},
		{ operation: props.node?.data?.operation, processName: props.node?.data?.process_name }
	);
	return fallback && !state.hidden;
});

const showProcessName = computed(() => {
	return currentActionType.value === "Process";
});

const showRuleField = computed(() => {
	return currentActionType.value === "Sub-Rule";
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
	const normalizedType = normalizeActionType(type);
	const op = props.node.data?.operation;
	if (normalizedType === "Sub-Rule") return false;
	const derived = getDerivedFieldState(
		normalizedType,
		"reference_docname",
		props.node?.data || {},
		store.rule_doc || {},
		{ operation: op, processName: props.node?.data?.process_name }
	);
	if (!derived.hidden) return true;

	if (normalizedType === "Query Records") {
		return op === "Query Report";
	}
	if (normalizedType === "Document Action") {
		return ["Update Existing", "Delete Record"].includes(op);
	}
	if (normalizedType === "Process" && op?.includes("Doc")) return true;

	return false;
});

const showInputSource = computed(() => {
	if (!contract.value) return false;
	return ["Query Records", "Document Action"].includes(props.node.data?.action_type);
});

const doctypeContext = computed(() => {
	const explicitDoctype = props.node?.data?.reference_doctype;
	if (explicitDoctype) return explicitDoctype;
	if (props.node?.data?.action_type === "Condition") {
		return store.rule_doc?.document_type || null;
	}
	return null;
});

const forcedReferenceDoctype = computed(() => {
	if (props.node.data?.action_type !== "Document Action") return null;
	if (props.node.data?.operation === "Add Comment") return "Comment";
	if (props.node.data?.operation === "Create ToDo") return "ToDo";
	return null;
});

// -- Field Definitions --
const referenceDoctypeField = computed(() => {
	const state = getDerivedFieldState(
		props.node.data?.action_type,
		"reference_doctype",
		props.node?.data || {},
		store.rule_doc || {},
		{
			operation: props.node?.data?.operation,
			processName: props.node?.data?.process_name,
		}
	);
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
		reqd: state.reqd ? 1 : 0,
		read_only: Boolean(forcedReferenceDoctype.value),
		description,
	};
});

const processNameField = computed(() => ({
	fieldname: "process_name",
	fieldtype: "Link",
	label: __("Process"),
	options: "Process",
	reqd: (contract.value?.required_fields || []).includes("process_name") ? 1 : 0,
}));

const ruleField = computed(() => ({
	fieldname: "rule",
	fieldtype: "Link",
	label: __("Sub-Rule"),
	options: "Rule",
	reqd: (contract.value?.required_fields || []).includes("rule") ? 1 : 0,
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
}));

const referenceDocnameField = computed(() => {
	const actionType = props.node?.data?.action_type;
	const operation = props.node?.data?.operation;
	const refDocType = props.node?.data?.reference_doctype;
	const state = getDerivedFieldState(
		actionType,
		"reference_docname",
		props.node?.data || {},
		store.rule_doc || {},
		{ operation, processName: props.node?.data?.process_name }
	);

	// Special case: Query Report
	if (actionType === "Query Records" && operation === "Query Report") {
		return {
			fieldname: "reference_docname",
			fieldtype: "Link",
			label: __("Report Name"),
			options: "Report",
			reqd: state.reqd ? 1 : 0,
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
			reqd: state.reqd ? 1 : 0,
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
		reqd: (contract.value?.required_fields || []).includes("operation") ? 1 : 0,
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

const groupedFields = computed(() => {
	const groups = {};
	const q = fieldSearchQuery.value.toLowerCase();

	doctypeFields.value.forEach((f) => {
		if (q && !f.fieldname.toLowerCase().includes(q) && !f.label.toLowerCase().includes(q)) {
			return;
		}

		const groupName = f.doctype || doctypeContext.value;
		if (!groups[groupName]) {
			groups[groupName] = { fields: [] };
		}
		groups[groupName].fields.push(f);
	});
	return groups;
});

function toggleGroup(groupName) {
	expandedGroups.value[groupName] = !expandedGroups.value[groupName];
}

function onDragStart(event, item, isField = false, groupName = "") {
	if (event.dataTransfer) {
		let path = "";
		if (isField) {
			if (groupName === doctypeContext.value || !groupName) {
				path = `doc.${item.fieldname}`;
			} else {
				// Child table field. If there's a loop iterator, use that?
				// Without active context, we just drag the raw fieldname or table.fieldname
				path = `${item.fieldname}`;
			}
		} else {
			path = item.value;
		}

		const text = `{{ ${path} }}`;
		event.dataTransfer.setData("text/plain", text);
		event.dataTransfer.setData("application/x-flexirule-variable", path);
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
	const dt = doctypeContext.value;
	if (!dt) {
		doctypeFields.value = [];
		return;
	}
	loadingFields.value = true;
	try {
		doctypeFields.value = await flexirule.utils.get_doctype_fields(dt);
		// Expand root group by default
		expandedGroups.value[dt] = true;
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
			applyOutputPolicyDefaults(props.node.data, {
				parent: store.rule_doc || {},
				preserveUserChoices: false,
			});
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
	() => doctypeContext.value,
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

/**
 * Smart insert: if a TextGeneratorControl is focused, insert directly.
 * Otherwise fall back to clipboard.
 */
function insertOrCopy(path) {
	const expr = `{{ ${path} }}`;
	const inserted = insertIntoActiveTGC(path);
	if (!inserted) {
		copyText(expr);
	} else {
		frappe?.show_alert?.({ message: `${__("Inserted")}: ${expr}`, indicator: "blue" }, 1);
	}
}

/** Build the Jinja path for a doc field based on its group context. */
function buildFieldPath(field, groupName) {
	if (!groupName || groupName === doctypeContext.value) return `doc.${field.fieldname}`;
	return field.fieldname;
}
</script>

<style scoped>
.input-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background-color: var(--fxr-bg-page);
}

.panel-header {
	padding: 18px 18px 14px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-surface);
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 15px;
	font-weight: 600;
}

.panel-tabs {
	display: flex;
	border-bottom: 1px solid var(--fxr-border-subtle);
	background-color: var(--fxr-surface);
	padding: 0 16px;
}
.tab-btn {
	background: none;
	border: none;
	padding: 12px 16px;
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-soft);
	cursor: pointer;
	border-bottom: 2px solid transparent;
	transition: all 0.2s;
}
.tab-btn:hover {
	color: var(--fxr-text-strong);
}
.tab-btn.active {
	color: var(--fxr-node-accent, var(--fxr-accent));
	border-bottom-color: var(--fxr-node-accent, var(--fxr-accent));
}

.panel-sections {
	flex: 1;
	overflow-y: auto;
	padding: var(--fxr-space-4, 12px);
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.panel-section {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 10px;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 10px;
	background-color: var(--fxr-surface-2);
}

.section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
}

.section-actions {
	display: inline-flex;
	align-items: center;
}

.section-title {
	margin: 0;
	font-size: 10px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--fxr-text-soft);
}

.section-divider {
	height: 1px;
	background-color: var(--fxr-border-subtle);
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
	padding: 4px 10px;
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 8px;
	font-size: 11px;
	cursor: grab;
	transition: all 0.2s;
}

.variable-item:hover {
	border-color: var(--fxr-node-accent, var(--fxr-accent));
	box-shadow: var(--fxr-shadow-sm);
	transform: translateX(1px);
}

.variable-label {
	font-weight: 600;
	color: var(--fxr-text-strong);
}

.variable-type {
	font-size: 9px;
	padding: 2px 6px;
	background-color: var(--fxr-surface-2);
	border-radius: 4px;
	color: var(--fxr-text-soft);
}

/* Tree Styles */
.tree-container {
	display: flex;
	flex-direction: column;
	font-size: 12px;
}
.tree-group {
	margin-bottom: 4px;
}
.tree-group-header {
	padding: 6px 8px;
	cursor: pointer;
	border-radius: 6px;
	color: var(--fxr-text-strong);
	font-weight: 600;
	display: flex;
	align-items: center;
	transition: background 0.15s;
}
.tree-group-header:hover {
	background-color: var(--fxr-bg-hover);
}
.tree-group-header .fa {
	font-size: 10px;
	width: 16px;
	color: var(--fxr-text-soft);
}
.tree-group-items {
	padding-left: 20px;
	border-left: 1px solid var(--fxr-border-subtle);
	margin-left: 12px;
	margin-top: 4px;
	display: flex;
	flex-direction: column;
	gap: 4px;
}
.tree-iterator-hint {
	padding: 4px 8px;
	margin-bottom: 4px;
	background-color: var(--fxr-surface-2);
	border-radius: 4px;
	font-size: 11px;
}
.tree-item {
	padding: 4px 8px;
	border-radius: 4px;
	display: flex;
	justify-content: space-between;
	cursor: grab;
	color: var(--fxr-text-soft);
}
.tree-item:hover {
	background-color: var(--fxr-bg-hover);
}
.tree-item-label {
	font-weight: 500;
}
.tree-item-type {
	font-size: 10px;
	color: var(--fxr-text-soft, var(--text-muted));
}

.tips-box {
	background-color: var(--fxr-surface);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 12px;
	padding: 12px;
	font-size: 12px;
	color: var(--fxr-text-soft);
}
.tips-box h6 {
	margin: 0 0 8px 0;
	font-size: 12px;
	font-weight: 600;
	color: var(--fxr-text-strong);
}
.tips-box ul {
	margin: 0;
	padding-left: 20px;
}
.tips-box li {
	margin-bottom: 4px;
}

.guide-content {
	background-color: var(--fxr-surface);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 12px;
}

.guide-icon-small {
	width: 24px;
	height: 24px;
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #ffffff;
	font-size: 12px;
}

.guide-text-small {
	font-size: 12px;
	line-height: 1.5;
	color: var(--fxr-text-soft);
	margin: 0;
}

.insight-label {
	font-size: 10px;
	font-weight: 700;
	color: var(--fxr-node-accent, var(--fxr-accent));
	text-transform: uppercase;
	display: block;
	margin-bottom: 4px;
}

.insight-text {
	font-size: 11px;
	color: var(--fxr-text-soft);
	background-color: var(--fxr-accent-soft);
	padding: 8px;
	border-radius: 8px;
	border-left: 3px solid var(--fxr-node-accent, var(--fxr-accent));
	margin: 0;
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}
.v2-scrollbar::-webkit-scrollbar-thumb {
	background-color: var(--fxr-border-strong);
	border-radius: 10px;
}

.empty-state {
	padding: 20px;
	text-align: center;
	color: var(--fxr-text-faint);
	font-size: 11px;
	background-color: var(--fxr-surface-2);
	border: 1px dashed var(--fxr-border-subtle);
	border-radius: 8px;
}

.section-collapsed-note {
	font-size: 11px;
	color: var(--fxr-text-faint);
	background-color: var(--fxr-surface);
	border: 1px dashed var(--fxr-border-subtle);
	border-radius: 8px;
	padding: 10px 12px;
}

:deep(.form-control:focus),
:deep(.awesomplete input:focus),
:deep(.multiselect__input:focus) {
	border-color: var(--fxr-node-accent, var(--fxr-border-focus)) !important;
	box-shadow: 0 0 0 2px var(--fxr-node-accent-light, var(--fxr-accent-light)) !important;
}

@media (max-width: 768px) {
	.panel-sections {
		padding: var(--fxr-space-4);
		gap: var(--fxr-space-5);
	}

	.section-header {
		flex-wrap: wrap;
	}

	.variable-list {
		max-height: 260px;
	}

	.variable-item {
		padding: var(--fxr-space-3) var(--fxr-space-4);
	}
}
</style>
