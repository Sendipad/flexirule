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

		<!-- Normal Condition Editor Row: Left -> Operator -> Right -->
		<template v-else>
			<div class="condition-main-row">
				<!-- 1. Left Operand (FlexValueControl with searchable source selector) -->
				<div class="condition-col operand-col left-col">
					<FlexValueControl
						v-model="leftValueModel"
						:context="leftControlContext"
						:placeholder="__('Choose a value source...')"
						:engine="store"
						:doc="store?.rule_doc"
						:variableOptions="variableOptions"
						:readOnly="readOnly"
						:disabled="readOnly"
						class="w-100 min-w-0"
					/>
				</div>

				<!-- 2. Operator Select: Disabled until left operand is chosen, shows only compatible operators from backend DTO -->
				<div class="condition-col operator-col">
					<SelectControl
						class="operator-select"
						:df="{
							fieldtype: 'Select',
							options: operatorOptions,
							reqd: 1,
							read_only: readOnly,
						}"
						:modelValue="node.operator"
						:read_only="readOnly"
						:disabled="readOnly || !hasLeftOperand"
						:hideLabel="true"
						@update:modelValue="onOperatorChange"
					/>
				</div>

				<!-- 3. Right Operand: Hidden if unary or no operator. Initializes blank without implicit 0/false -->
				<div v-if="hasLeftOperand && node.operator && !isUnary" class="condition-col operand-col right-col">
					<FlexValueControl
						v-model="rightValueModel"
						:context="rightControlContext"
						:placeholder="__('Enter comparison value...')"
						:engine="store"
						:doc="store?.rule_doc"
						:variableOptions="variableOptions"
						:readOnly="readOnly"
						:disabled="readOnly"
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

				<!-- Action (Remove) -->
				<div v-if="!readOnly" class="condition-col action-col">
					<button
						type="button"
						class="fxr-btn fxr-btn--icon fxr-btn--danger"
						@click="$emit('remove')"
						:title="__('Remove')"
					>
						<i class="fa fa-trash"></i>
					</button>
				</div>
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
import { computed } from "vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import SelectControl from "../../controls/SelectControl.vue";
import UnsupportedConditionCard from "./UnsupportedConditionCard.vue";
import {
	UNARY_OPERATORS,
	toCanonicalFlexValue,
	fieldExpressionToCanonicalVariable,
} from "./canonical_condition_adapter.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	contract: { type: Object, default: () => ({}) },
	docFields: { type: Array, default: () => [] },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	store: { type: Object, default: null },
	currentDocType: { type: String, default: "" },
	errors: { type: Array, default: () => [] },
	isSoleCondition: { type: Boolean, default: false },
	isEntryNode: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change", "remove", "replace"]);

const hasLeftOperand = computed(() => {
	const left = props.node.left;
	if (!left) return false;
	if (typeof left === "string") return left.trim().length > 0;
	if (typeof left === "object") {
		if (left.mode === "variable") {
			return !!(left.path?.scope && (left.path?.segments?.length || left.path.scope === "doctype"));
		}
		if (left.mode === "static") {
			return left.value !== undefined && left.value !== null && left.value !== "";
		}
		if (left.mode === "resolver") {
			return !!(left.family && left.operation);
		}
		return true;
	}
	return false;
});

const isUnary = computed(() => {
	const op = props.node.operator;
	if (!op) return false;
	const spec = props.contract?.operators?.[op];
	return UNARY_OPERATORS.has(op) || spec?.arity === 1;
});

// Resolve operand metadata descriptor from Frappe DocField metadata and the backend-owned contract.
const leftOperandDescriptor = computed(() => {
	const left = props.node.left;
	const fieldtypeValueTypes = props.contract?.fieldtype_value_types || {};
	const base = {
		fieldtype: "Data",
		value_type: fieldtypeValueTypes.Data?.[0] || "string",
		value_types: fieldtypeValueTypes.Data || ["string"],
		doctype: props.currentDocType,
		fieldname: null,
		options: null,
		label: "",
		source_identity: null,
		allowed_modes: props.contract?.flexvalue_modes || {},
	};

	if (!left) return base;

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
			const valueTypes = fieldtypeValueTypes[fieldtype] || ["string"];
			return {
				...base,
				fieldtype,
				value_types: valueTypes,
				value_type: valueTypes.includes("decimal") ? "decimal" : valueTypes[0] || "string",
				doctype:
					match.doctype ||
					(["Link", "Dynamic Link"].includes(fieldtype)
						? match.options
						: props.currentDocType),
				fieldname: match.fieldname || segments[segments.length - 1] || null,
				options: match.options || null,
				label: match.label || match.friendlyLabel || fullPath,
				source_identity: { scope, segments: [...segments] },
			};
		}
		return { ...base, source_identity: { scope, segments: [...segments] }, label: fullPath };
	}

	if (left?.mode === "resolver") {
		const resType = left.value_type || "string";
		return {
			...base,
			fieldtype: resType === "integer" ? "Int" : resType === "decimal" ? "Float" : "Data",
			value_type: resType,
			value_types: [resType],
			label: `${left.family}.${left.operation}`,
		};
	}

	if (left?.mode === "static") {
		const valueType = left.value_type || "string";
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
		onUpdate: onLeftOperandChange,
	};
});

// Exclusively use backend operator registry DTO
const operatorOptions = computed(() => {
	if (!hasLeftOperand.value) {
		return [{ label: __("Select a left value first"), value: "" }];
	}

	const contractOps = props.contract?.operators;
	const desc = leftOperandDescriptor.value;
	const ft = desc.fieldtype;
	const valueTypes = desc.value_types || (desc.value_type ? [desc.value_type] : []);

	let candidates = [];
	if (contractOps && Object.keys(contractOps).length > 0) {
		candidates = Object.values(contractOps);
	} else if (Array.isArray(props.contract?.operatorList) && props.contract.operatorList.length > 0) {
		candidates = props.contract.operatorList;
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

	return [
		{ label: __("Choose comparison..."), value: "" },
		...filtered.map((op) => ({
			label: op.label || op.id,
			value: op.id,
		})),
	];
});

const rightControlContext = computed(() => {
	const desc = leftOperandDescriptor.value;
	const op = props.node.operator;

	const df = {
		fieldtype: desc.fieldtype,
		options: desc.options,
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
		filters: {},
		allowResolvers: true,
	};
});

const nodeErrors = computed(() => {
	const errs = [...(props.errors || [])];
	if (props.node._invalid_right_error) {
		errs.push(props.node._invalid_right_error);
	}
	return errs;
});

const hasError = computed(() => nodeErrors.value.length > 0 || props.node.is_unsupported);

const leftValueModel = computed({
	get() {
		return props.node.left || null;
	},
	set(val) {
		let canonical = val;
		if (typeof val === "string") {
			canonical = fieldExpressionToCanonicalVariable(val);
		} else if (val && typeof val === "object" && !val.mode) {
			canonical = toCanonicalFlexValue(val);
		}
		props.node.left = canonical;

		// When left changes, verify if current operator remains compatible; if not, reset operator
		if (props.node.operator) {
			const compatible = operatorOptions.value.some((o) => o.value === props.node.operator);
			if (!compatible) {
				props.node.operator = "";
				props.node.right = null;
			}
		}

		emit("change", props.node);
	},
});

const rightValueModel = computed({
	get() {
		if (props.node._draft_invalid_right !== undefined) {
			return props.node._draft_invalid_right;
		}
		return props.node.right || null;
	},
	set(val) {
		let canonical = val;
		delete props.node._draft_invalid_right;
		delete props.node._invalid_right_error;

		try {
			canonical = toCanonicalFlexValue(
				val,
				leftOperandDescriptor.value.fieldtype,
				props.node.operator
			);
			props.node.right = canonical;
		} catch (err) {
			const errMsg = err?.message || "Invalid value format for declared fieldtype";
			props.node._draft_invalid_right = val;
			props.node._invalid_right_error = errMsg;
		}
		emit("change", props.node);
	},
});

function onLeftOperandChange() {
	emit("change", props.node);
}

function onOperatorChange(newOp) {
	props.node.operator = newOp;
	const isNewUnary =
		UNARY_OPERATORS.has(newOp) || props.contract?.operators?.[newOp]?.arity === 1;

	if (isNewUnary) {
		if (props.node.right) {
			props.node._draft_right = props.node.right;
			props.node.right = null;
		}
	} else {
		// Initialize blank static value ready for input without implicit defaults
		const isMembership = newOp === "in" || newOp === "not_in";
		if (isMembership) {
			props.node.right = {
				mode: "static",
				value_type: "list",
				value: [],
			};
		} else {
			props.node.right = {
				mode: "static",
				value_type: leftOperandDescriptor.value.value_type || "string",
				value: "",
			};
		}
	}
	emit("change", props.node);
}

function clearPreservedDraftRight() {
	delete props.node._draft_right;
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
	grid-template-columns: 1.8fr 1.2fr 2.4fr auto;
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

.action-col .fxr-btn--danger {
	color: var(--fxr-text-danger, #ef4444);
	opacity: 0.8;
}

.action-col .fxr-btn--danger:hover {
	opacity: 1;
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
