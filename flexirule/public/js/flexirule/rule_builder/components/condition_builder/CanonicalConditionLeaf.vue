<template>
	<div class="canonical-condition-leaf" :class="{ 'is-invalid': hasError }">
		<!-- Preserved Unsupported Condition Card -->
		<UnsupportedConditionCard
			v-if="node.is_unsupported"
			:node="node"
			:readOnly="readOnly"
			:isSoleCondition="isSoleCondition"
			:isEntryNode="isEntryNode"
			@replace="onReplaceUnsupported"
			@remove="$emit('remove')"
		/>

		<!-- Normal Condition Editor Row -->
		<template v-else>
			<div class="condition-main-row">
				<!-- Left Operand (FlexValueControl) -->
				<div class="condition-col operand-col left-col">
					<FlexValueControl
						ref="leftControlRef"
						v-model="leftValueModel"
						:context="leftControlContext"
						:doctype="currentDocType"
						:docFields="docFields"
						:variableOptions="variableOptions"
						:placeholder="__('Choose a field, variable, or resolver (@)...')"
						:engine="store"
						:doc="store?.rule_doc"
						:readOnly="readOnly"
						:disabled="readOnly"
						:showValidation="showValidation"
						class="w-100 min-w-0 left-operand-control"
					/>
				</div>

				<!-- Operator Select -->
				<div class="condition-col operator-col">
					<div
						v-if="contractLoading"
						class="operator-loading-state text-muted small d-flex align-items-center"
					>
						<i class="fa fa-spinner fa-spin mr-1"></i>
						<span>{{ __("Loading comparisons...") }}</span>
					</div>
					<div
						v-else-if="contractError"
						class="operator-error-state small text-danger d-flex align-items-center justify-content-between"
					>
						<span
							><i class="fa fa-exclamation-circle mr-1"></i
							>{{ __("Error loading operators") }}</span
						>
						<button
							type="button"
							class="btn btn-link btn-xs p-0 text-primary ml-1"
							@click="$emit('retry-contract')"
						>
							{{ __("Retry") }}
						</button>
					</div>
					<SelectControl
						v-else
						class="operator-select"
						:df="{
							fieldtype: 'Select',
							options: operatorOptions,
							reqd: 1,
							read_only: readOnly,
						}"
						:modelValue="node.operator"
						:read_only="readOnly"
						:disabled="readOnly || !node.left || isContractUnavailable"
						:hideLabel="true"
						@update:modelValue="onOperatorChange"
					/>
				</div>

				<!-- Right Operand (FlexValueControl with metadata descriptor) -->
				<div v-if="node.operator && !isUnary" class="condition-col operand-col right-col">
					<FlexValueControl
						v-model="rightValueModel"
						:context="rightControlContext"
						:doctype="currentDocType"
						:docFields="docFields"
						:variableOptions="variableOptions"
						placeholder="Choose a comparison value"
						:engine="store"
						:doc="store?.rule_doc"
						:readOnly="readOnly"
						:disabled="readOnly"
						:showValidation="showValidation"
						class="w-100 min-w-0"
					/>
				</div>
				<div v-else class="condition-col empty-col">
					<div
						v-if="node._draft_right"
						class="unary-draft-indicator small text-muted d-flex align-items-center justify-content-between px-2 py-1 bg-light rounded"
					>
						<span>{{ __("Value preserved in draft") }}</span>
						<button
							type="button"
							class="btn btn-link btn-xs p-0 text-danger"
							@click="clearPreservedDraftRight"
						>
							{{ __("Clear") }}
						</button>
					</div>
				</div>
			</div>

			<!-- Incompatibility Warning -->
			<div
				v-if="showValidation && incompatibilityWarning"
				class="alert alert-warning py-1 px-2 small mt-2 mb-0 d-flex align-items-center justify-content-between"
			>
				<div>
					<i class="fa fa-exclamation-triangle mr-1"></i>
					<span>{{ incompatibilityWarning }}</span>
				</div>
				<button
					v-if="!readOnly"
					type="button"
					class="btn btn-xs btn-outline-warning ml-2"
					@click="resetRightOperand"
				>
					{{ __("Clear Value") }}
				</button>
			</div>

			<!-- Errors List -->
			<div v-if="nodeErrors.length" class="node-errors mt-1">
				<div v-for="(err, idx) in nodeErrors" :key="idx" class="text-danger small">
					<i class="fa fa-info-circle mr-1"></i>{{ err }}
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import SelectControl from "../../controls/SelectControl.vue";
import UnsupportedConditionCard from "./UnsupportedConditionCard.vue";
import {
	toCanonicalFlexValue,
	fieldExpressionToCanonicalVariable,
} from "./canonical_condition_adapter.mjs";
import { isLeafComplete } from "./canonical_condition_validation.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	contract: { type: Object, default: () => ({}) },
	contractLoading: { type: Boolean, default: false },
	contractError: { type: String, default: "" },
	docFields: { type: Array, default: () => [] },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	store: { type: Object, default: null },
	currentDocType: { type: String, default: "" },
	errors: { type: Array, default: () => [] },
	isSoleCondition: { type: Boolean, default: false },
	isEntryNode: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change", "remove", "replace", "retry-contract"]);

const isUnary = computed(() => {
	const op = props.node.operator;
	if (!op) return false;
	const spec = props.contract?.operators?.[op];
	return spec?.arity === 1;
});

// Resolve operand metadata from Frappe DocField metadata and the backend-owned type contract.
function normalizeLinkFilters(rawFilters) {
	if (!rawFilters) return null;
	if (typeof rawFilters === "string") {
		try {
			return JSON.parse(rawFilters);
		} catch {
			return null;
		}
	}
	return typeof rawFilters === "object" ? rawFilters : null;
}

const leftOperandDescriptor = computed(() => {
	const left = props.node.left;
	const fieldtypeValueTypes = props.contract?.fieldtype_value_types || {};
	const base = {
		fieldtype: "Data",
		value_type: fieldtypeValueTypes.Data?.[0] || "string",
		value_types: fieldtypeValueTypes.Data || [],
		doctype: props.currentDocType,
		fieldname: null,
		options: null,
		filters: null,
		label: "",
		source_identity: null,
		allowed_modes: props.contract?.flexvalue_modes || {},
	};

	if (left?.mode === "variable") {
		const path = left.path || {};
		const scope = path.scope || "doc";
		const segments = Array.isArray(path.segments) ? path.segments : [];
		const fullPath = segments.length ? scope + "." + segments.join(".") : scope;
		const allFields = [...props.docFields, ...props.variableOptions];
		const match = allFields.find((field) => {
			const value = field?.value ?? field;
			return (
				value === fullPath ||
				(scope === "doc" && (value === segments[0] || field?.fieldname === segments[0])) ||
				(scope !== "doc" && value === scope + "." + segments.join("."))
			);
		});
		if (match) {
			const fieldtype = match.fieldtype || "Data";
			const valueTypes = fieldtypeValueTypes[fieldtype] || [];
			return {
				...base,
				fieldtype,
				value_types: valueTypes,
				value_type:
					fieldtype === "Check" && valueTypes.includes("Check")
						? "Check"
						: valueTypes.includes("decimal")
							? "decimal"
						: valueTypes[0] || null,
				doctype:
					match.doctype ||
					(["Link", "Dynamic Link"].includes(fieldtype)
						? match.options
						: props.currentDocType),
				fieldname: match.fieldname || segments[segments.length - 1] || null,
				options: match.options || null,
				filters: normalizeLinkFilters(match.link_filters || match.filters),
				label: match.label || match.friendlyLabel || fullPath,
				source_identity: { scope, segments: [...segments] },
			};
		}
		return { ...base, source_identity: { scope, segments: [...segments] }, label: fullPath };
	}

	if (left?.mode === "static") {
		const valueType = left.value_type || null;
		const matchingFieldtype = Object.entries(fieldtypeValueTypes).find(
			([, types]) => Array.isArray(types) && types.includes(valueType)
		)?.[0];
		return {
			...base,
			fieldtype: matchingFieldtype || "Data",
			value_type: valueType || base.value_type,
			value_types: valueType ? [valueType] : base.value_types,
		};
	}

	if (left?.mode === "resolver") {
		const fam = left.family;
		const op = left.operation;
		const declaredVt = left.value_type;
		const resolvers = props.contract?.flexvalue_modes?.resolver || [];
		const spec = Array.isArray(resolvers)
			? resolvers.find((r) => r.family === fam && r.operation === op)
			: null;

		let outputFt = spec?.output_type || declaredVt || "Data";
		// Normalize output type if it's already a semantic alias (e.g. Float -> decimal, Int -> integer)
		const valueTypes = fieldtypeValueTypes[outputFt] || [outputFt.toLowerCase()];
		const semanticVt = valueTypes[0] || "string";

		return {
			...base,
			fieldtype: outputFt,
			value_type: semanticVt,
			value_types: valueTypes,
			label: spec?.label || `${fam}.${op}`,
		};
	}

	return base;
});

const leftControlContext = computed(() => {
	const desc = leftOperandDescriptor.value;
	return {
		df: {
			fieldtype: desc.fieldtype,
			fieldname: desc.fieldname || undefined,
			options: desc.options,
			label: desc.label,
			reqd: 1,
		},
		referenceDoctype: desc.doctype,
		resolvedOperand: desc,
		isLeftOperand: true,
		conditionContract: props.contract,
		onUpdate: onLeftOperandChange,
	};
});
function formatOperatorLabel(label) {
	if (!label) return "";
	const translated = globalThis.__ ? globalThis.__(label) : label;
	if (typeof translated !== "string" || !translated.length) return "";
	// Locale-safe capitalization of the first character if case conversion is supported
	const first = translated.charAt(0);
	const upper = first.toUpperCase();
	return upper !== first.toLowerCase() ? upper + translated.slice(1) : translated;
}

const isContractUnavailable = computed(() => {
	const contractOps = props.contract?.operators;
	const list = props.contract?.operatorList;
	return !(
		(contractOps && Object.keys(contractOps).length > 0) ||
		(Array.isArray(list) && list.length > 0)
	);
});

const operatorOptions = computed(() => {
	const contractOps = props.contract?.operators;
	const desc = leftOperandDescriptor.value;
	const ft = desc.fieldtype;
	const valueTypes = desc.value_types || (desc.value_type ? [desc.value_type] : []);

	let candidates = [];
	if (contractOps && Object.keys(contractOps).length > 0) {
		candidates = Object.values(contractOps);
	} else if (
		Array.isArray(props.contract?.operatorList) &&
		props.contract.operatorList.length > 0
	) {
		candidates = props.contract.operatorList;
	} else {
		// Contract unavailable - fail closed without guessing fallback operators
		return [{ label: __("Loading comparisons..."), value: "" }];
	}

	const filtered = candidates.filter((opSpec) => {
		if (opSpec.fieldtypes && Array.isArray(opSpec.fieldtypes)) {
			if (!opSpec.fieldtypes.includes(ft)) return false;
		}
		if (opSpec.accepted_left_types && Array.isArray(opSpec.accepted_left_types)) {
			if (!valueTypes.some((valueType) => opSpec.accepted_left_types.includes(valueType))) {
				return false;
			}
		}
		return true;
	});

	if (filtered.length === 0) {
		return [{ label: __("No compatible comparisons"), value: "" }];
	}

	// Deduplicate choices by canonical ID
	const seenIds = new Set();
	const uniqueFiltered = [];
	for (const op of filtered) {
		if (!seenIds.has(op.id)) {
			seenIds.add(op.id);
			uniqueFiltered.push(op);
		}
	}

	return [
		{ label: __("Choose how the value should match"), value: "" },
		...uniqueFiltered.map((op) => ({
			label: formatOperatorLabel(op.label || op.id),
			value: op.id,
		})),
	];
});

const rightControlContext = computed(() => {
	const desc = leftOperandDescriptor.value;
	const op = props.node.operator;
	const isListOp = op === "in" || op === "not_in";

	const df = {
		fieldtype: desc.fieldtype,
		options: desc.options,
		filters: desc.filters,
		link_filters: desc.filters,
		label: desc.label,
		reqd: 1,
	};

	let refDocType = desc.doctype || props.currentDocType;
	if (desc.fieldtype === "Link" && desc.options) {
		refDocType = desc.options;
	}

	return {
		df,
		operator: op,
		referenceDoctype: refDocType,
		filters: desc.filters || null,
	};
});

const incompatibilityWarning = ref("");

function checkIncompatibility() {
	if (isUnary.value) {
		incompatibilityWarning.value = "";
		return;
	}

	const op = props.node.operator;
	const opSpec = props.contract?.operators?.[op];
	const right = props.node.right;

	if (!right || !opSpec) {
		incompatibilityWarning.value = "";
		return;
	}

	const acceptedRightTypes = opSpec.accepted_right_types || [];
	if (acceptedRightTypes.length > 0 && right.mode === "static") {
		const vt = right.value_type || "string";
		if (!acceptedRightTypes.includes(vt) && vt !== "null") {
			incompatibilityWarning.value = __(
				"This value may not be compatible with the selected comparison. Please review it."
			);
			return;
		}
	}
	incompatibilityWarning.value = "";
}

const rightCoercionError = ref("");

const nodeErrors = computed(() => {
	if (!props.showValidation) return [];
	const errs = [...(props.errors || [])];
	if (rightCoercionError.value) {
		errs.push(rightCoercionError.value);
	} else if (props.node._invalid_right_error) {
		errs.push(props.node._invalid_right_error);
	}
	if (incompatibilityWarning.value) {
		errs.push(incompatibilityWarning.value);
	}
	return errs;
});

const hasError = computed(
	() => (props.showValidation && nodeErrors.value.length > 0) || props.node.is_unsupported
);

function syncDraftStatus() {
	if (isLeafComplete(props.node, props.contract)) {
		delete props.node.is_incomplete_draft;
	} else {
		props.node.is_incomplete_draft = true;
	}
}

const leftValueModel = computed({
	get() {
		return props.node.left || "";
	},
	set(val) {
		let canonical = val;
		if (typeof val === "string") {
			canonical = fieldExpressionToCanonicalVariable(val);
		} else if (val && typeof val === "object" && !val.mode) {
			canonical = toCanonicalFlexValue(val);
		}
		props.node.left = canonical;
		syncDraftStatus();
		emit("change", props.node);
	},
});

const rightValueModel = computed({
	get() {
		if (props.node._draft_invalid_right !== undefined) {
			return props.node._draft_invalid_right;
		}
		return props.node.right || "";
	},
	set(val) {
		let canonical = val;
		rightCoercionError.value = "";
		delete props.node._draft_invalid_right;
		delete props.node._invalid_right_error;

		try {
			canonical = toCanonicalFlexValue(
				val,
				leftOperandDescriptor.value.fieldtype,
				props.node.operator
			);
			if (
				["in", "not_in"].includes(props.node.operator) &&
				canonical.mode === "static" &&
				(canonical.value_type !== "list" || !Array.isArray(canonical.value))
			) {
				throw new TypeError("Membership comparisons require a list of values");
			}
			props.node.right = canonical;
		} catch (err) {
			const errMsg = err?.message || "Invalid value format for declared fieldtype";
			rightCoercionError.value = errMsg;
			props.node._draft_invalid_right = val;
			props.node._invalid_right_error = errMsg;
		}
		syncDraftStatus();
		checkIncompatibility();
		emit("change", props.node);
	},
});

function onLeftOperandChange() {
	const currentOp = props.node.operator;
	const availableOps = operatorOptions.value.map((o) => o.value).filter(Boolean);

	if (!currentOp || !availableOps.includes(currentOp)) {
		if (availableOps.length > 0) {
			const preferredOp = availableOps.includes("eq") ? "eq" : availableOps[0];
			onOperatorChange(preferredOp);
			return;
		} else {
			props.node.operator = "";
		}
	}

	syncDraftStatus();
	checkIncompatibility();
	emit("change", props.node);
}

function onOperatorChange(newOp) {
	props.node.operator = newOp;
	const opSpec = props.contract?.operators?.[newOp];
	const isNewUnary = opSpec?.arity === 1;

	if (isNewUnary) {
		if (props.node.right) {
			props.node._draft_right = props.node.right;
			props.node.right = null;
		}
	} else {
		if (!props.node.right) {
			if (props.node._draft_right) {
				props.node.right = props.node._draft_right;
				delete props.node._draft_right;
			} else {
				props.node.right = {
					mode: "static",
					value_type: leftOperandDescriptor.value.value_type || "string",
					value: "",
				};
			}
		}
	}
	syncDraftStatus();
	checkIncompatibility();
	emit("change", props.node);
}

function clearPreservedDraftRight() {
	delete props.node._draft_right;
	emit("change", props.node);
}

function resetRightOperand() {
	delete props.node._draft_invalid_right;
	delete props.node._invalid_right_error;
	rightCoercionError.value = "";
	props.node.right = {
		mode: "static",
		value_type: leftOperandDescriptor.value.value_type || "string",
		value: "",
	};
	incompatibilityWarning.value = "";
	emit("change", props.node);
}

function onReplaceUnsupported() {
	props.node.is_unsupported = false;
	props.node.is_incomplete_draft = true;
	props.node.operator = "";
	props.node.left = null;
	props.node.right = null;
	delete props.node.original_payload;
	delete props.node.unsupported_reason;
	emit("change", props.node);
}

watch(
	() => props.node.operator,
	() => {
		checkIncompatibility();
	}
);
</script>

<style scoped>
.canonical-condition-leaf {
	background: var(--fxr-bg-card, #ffffff);
	border: 1px solid var(--fxr-border, #e5e7eb);
	border-radius: var(--fxr-radius-md, 6px);
	padding: var(--fxr-space-1, 4px) var(--fxr-space-2, 8px);
	transition: border-color var(--fxr-transition-fast), background-color var(--fxr-transition-fast);
}

.canonical-condition-leaf:hover {
	border-color: var(--fxr-border-strong, #cbd5e1);
}

.canonical-condition-leaf.is-invalid {
	border-color: var(--fxr-text-danger, #ef4444) !important;
	background-color: var(--fxr-danger-soft, #fef2f2) !important;
	box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.1);
}

.condition-main-row {
	display: grid;
	grid-template-columns: 1.8fr 1.2fr 2.4fr;
	gap: var(--fxr-space-2, 8px);
	align-items: center;
	position: relative;
	z-index: 1;
}

.condition-col {
	min-width: 0;
}

.operator-select {
	width: 100%;
	min-width: 100px;
	font-weight: var(--fxr-weight-semibold, 600);
	color: var(--fxr-text-strong, #1f2937);
	background-color: var(--fxr-surface-2, #f3f4f6);
}

@media (max-width: 768px) {
	.condition-main-row {
		display: flex;
		flex-direction: column;
		gap: var(--fxr-space-2, 8px);
		align-items: stretch;
	}
	.condition-col {
		width: 100%;
	}
}
</style>
