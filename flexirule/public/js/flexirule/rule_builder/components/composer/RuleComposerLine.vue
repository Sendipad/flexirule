<template>
	<div class="rule-composer-line" :class="{ 'is-invalid': hasError, 'is-focused': isFocused }">
		<!-- Left Operand Display / Input -->
		<div class="composer-segment left-segment">
			<!-- If token exists, display ComposerToken -->
			<div v-if="node.left" class="token-container">
				<ComposerToken
					:modelValue="node.left"
					:readOnly="readOnly"
					@click="onEditLeft"
					@remove="onRemoveLeft"
				/>
			</div>

			<!-- Otherwise, display active input with @ prompt -->
			<div v-else class="composer-input-wrapper">
				<button
					ref="leftButtonRef"
					type="button"
					class="composer-mention-trigger"
					:disabled="readOnly"
					@click="openLeftPalette"
				>
					<span class="mention-at">@</span>
					<span class="mention-placeholder">{{
						__("field, variable or resolver...")
					}}</span>
				</button>
			</div>

			<!-- Suggestion Palette for Left Operand -->
			<SuggestionPalette
				:isOpen="isLeftPaletteOpen"
				:anchorEl="leftButtonRef"
				:docFields="docFields"
				:variableOptions="variableOptions"
				:contract="contract"
				:isConditionOperand="true"
				@select="onSelectLeft"
				@close="isLeftPaletteOpen = false"
			/>
		</div>

		<!-- Operator Token -->
		<div class="composer-segment operator-segment">
			<InlineOperatorToken
				:modelValue="node.operator"
				:contract="contract"
				:leftFieldtype="leftDescriptor.fieldtype"
				:leftValueType="leftDescriptor.value_type"
				:leftValueTypes="leftDescriptor.value_types"
				:readOnly="readOnly"
				:disabled="readOnly || !node.left"
				@update:modelValue="onOperatorChange"
			/>
		</div>

		<!-- Right Operand Composer (Omitted if unary) -->
		<div v-if="node.operator && !isUnary" class="composer-segment right-segment">
			<!-- If token exists and is variable/resolver, show token -->
			<div v-if="node.right && node.right.mode !== 'static'" class="token-container">
				<ComposerToken
					:modelValue="node.right"
					:readOnly="readOnly"
					@click="onEditRight"
					@remove="onRemoveRight"
				/>
			</div>

			<!-- Static value input or @ trigger -->
			<div v-else class="right-input-container">
				<FlexValueControl
					v-model="rightModel"
					:context="rightControlContext"
					:placeholder="__('value or type @...')"
					:engine="store"
					:doc="store?.rule_doc"
					:variableOptions="variableOptions"
					:readOnly="readOnly"
					:disabled="readOnly"
					class="w-100 min-w-0"
				/>
				<button
					v-if="!readOnly"
					ref="rightMentionBtnRef"
					type="button"
					class="right-at-btn"
					:title="__('Mention dynamic variable or resolver')"
					@click="openRightPalette"
				>
					@
				</button>
			</div>

			<!-- Suggestion Palette for Right Operand -->
			<SuggestionPalette
				:isOpen="isRightPaletteOpen"
				:anchorEl="rightMentionBtnRef"
				:docFields="docFields"
				:variableOptions="variableOptions"
				:contract="contract"
				:isConditionOperand="true"
				:targetFieldtype="leftDescriptor.fieldtype"
				@select="onSelectRight"
				@close="isRightPaletteOpen = false"
			/>
		</div>

		<!-- Unary indicator when draft right is preserved -->
		<div v-else-if="node._draft_right" class="composer-segment preserved-draft-segment">
			<span class="text-muted small">{{ __("Preserved draft right") }}</span>
			<button
				v-if="!readOnly"
				type="button"
				class="btn btn-link btn-xs text-danger p-0 ml-1"
				@click="clearPreservedDraftRight"
			>
				{{ __("Clear") }}
			</button>
		</div>

		<!-- Action: Remove Condition Line -->
		<div v-if="!readOnly" class="composer-segment action-segment">
			<button
				type="button"
				class="composer-remove-btn"
				:title="__('Remove condition line')"
				@click="$emit('remove')"
			>
				<i class="fa fa-times"></i>
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import InlineOperatorToken from "./InlineOperatorToken.vue";
import ComposerToken from "./ComposerToken.vue";
import SuggestionPalette from "./SuggestionPalette.vue";
import {
	UNARY_OPERATORS,
	toCanonicalFlexValue,
	fieldExpressionToCanonicalVariable,
} from "../condition_builder/canonical_condition_adapter.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	contract: { type: Object, default: () => ({}) },
	docFields: { type: Array, default: () => [] },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	store: { type: Object, default: null },
	currentDocType: { type: String, default: "" },
	errors: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "change", "remove"]);

const isFocused = ref(false);
const isLeftPaletteOpen = ref(false);
const isRightPaletteOpen = ref(false);
const leftButtonRef = ref(null);
const rightMentionBtnRef = ref(null);

const isUnary = computed(() => {
	const op = props.node.operator;
	const spec = (props.contract?.operators || []).find
		? (props.contract?.operators || []).find((x) => x.id === op)
		: props.contract?.operators?.[op];
	return UNARY_OPERATORS.has(op) || spec?.arity === 1;
});

const leftDescriptor = computed(() => {
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
	};

	if (!left) return base;

	if (left.mode === "variable") {
		const path = left.path || {};
		const scope = path.scope || "doc";
		const segments = Array.isArray(path.segments) ? path.segments : [];
		const fullPath = segments.length ? `${scope}.${segments.join(".")}` : scope;
		const allFields = [...props.docFields, ...props.variableOptions];
		const match = allFields.find((f) => {
			const v = f?.value ?? f;
			return (
				v === fullPath ||
				(scope === "doc" && (v === segments[0] || f?.fieldname === segments[0])) ||
				(scope !== "doc" && v === `${scope}.${segments.join(".")}`)
			);
		});
		if (match) {
			const ft = match.fieldtype || "Data";
			const vts = fieldtypeValueTypes[ft] || ["string"];
			return {
				...base,
				fieldtype: ft,
				value_types: vts,
				value_type: vts.includes("decimal") ? "decimal" : vts[0] || "string",
				doctype:
					match.doctype ||
					(["Link", "Dynamic Link"].includes(ft) ? match.options : props.currentDocType),
				fieldname: match.fieldname || segments[segments.length - 1] || null,
				options: match.options || null,
				label: match.label || match.friendlyLabel || fullPath,
				source_identity: { scope, segments: [...segments] },
			};
		}
		return {
			...base,
			label: fullPath,
			source_identity: { scope, segments: [...segments] },
		};
	}

	if (left.mode === "resolver") {
		const resType = left.value_type || "string";
		return {
			...base,
			fieldtype: resType === "integer" ? "Int" : resType === "decimal" ? "Float" : "Data",
			value_type: resType,
			value_types: [resType],
			label: `@${left.family}.${left.operation}`,
		};
	}

	if (left.mode === "static") {
		const vt = left.value_type || "string";
		const matchingFt = Object.entries(fieldtypeValueTypes).find(
			([, types]) => Array.isArray(types) && types.includes(vt)
		)?.[0];
		return {
			...base,
			fieldtype: matchingFt || "Data",
			value_type: vt,
			value_types: [vt],
		};
	}

	return base;
});

const rightControlContext = computed(() => {
	const desc = leftDescriptor.value;
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

function openLeftPalette() {
	if (props.readOnly) return;
	isLeftPaletteOpen.value = true;
}

function onSelectLeft(suggestion) {
	isLeftPaletteOpen.value = false;
	props.node.left = suggestion.payload;

	// Reset operator if current operator is incompatible with new left
	if (props.node.operator) {
		const ops = props.contract?.operators || [];
		const opList = Array.isArray(ops) ? ops : Object.values(ops);
		const ft = leftDescriptor.value.fieldtype;
		const vts = leftDescriptor.value.value_types;
		const isCompatible = opList.some((spec) => {
			if (spec.id !== props.node.operator) return false;
			if (spec.fieldtypes && !spec.fieldtypes.includes(ft)) return false;
			if (spec.accepted_left_types && !vts.some((v) => spec.accepted_left_types.includes(v)))
				return false;
			return true;
		});

		if (!isCompatible) {
			props.node.operator = "";
			props.node.right = null;
		} else if (!props.node.right && !isUnary.value) {
			props.node.right = {
				mode: "static",
				value_type: leftDescriptor.value.value_type || "string",
				value: "",
			};
		}
	}
	emit("change", props.node);
}

function onEditLeft() {
	if (props.readOnly) return;
	isLeftPaletteOpen.value = true;
}

function onRemoveLeft() {
	if (props.readOnly) return;
	props.node.left = null;
	props.node.operator = "";
	props.node.right = null;
	emit("change", props.node);
}

function openRightPalette() {
	if (props.readOnly) return;
	isRightPaletteOpen.value = true;
}

function onSelectRight(suggestion) {
	isRightPaletteOpen.value = false;
	props.node.right = suggestion.payload;
	emit("change", props.node);
}

function onEditRight() {
	if (props.readOnly) return;
	isRightPaletteOpen.value = true;
}

function onRemoveRight() {
	if (props.readOnly) return;
	props.node.right = {
		mode: "static",
		value_type: leftDescriptor.value.value_type || "string",
		value: "",
	};
	emit("change", props.node);
}

const rightModel = computed({
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
				leftDescriptor.value.fieldtype,
				props.node.operator
			);
			props.node.right = canonical;
		} catch (err) {
			const msg = err?.message || "Invalid value format for declared fieldtype";
			props.node._draft_invalid_right = val;
			props.node._invalid_right_error = msg;
		}
		emit("change", props.node);
	},
});

function onOperatorChange(newOp) {
	props.node.operator = newOp;
	const spec = (props.contract?.operators || []).find
		? (props.contract?.operators || []).find((x) => x.id === newOp)
		: props.contract?.operators?.[newOp];
	const isNewUnary = UNARY_OPERATORS.has(newOp) || spec?.arity === 1;

	if (isNewUnary) {
		if (props.node.right) {
			props.node._draft_right = props.node.right;
			props.node.right = null;
		}
	} else {
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
				value_type: leftDescriptor.value.value_type || "string",
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

const hasError = computed(
	() => (props.errors || []).length > 0 || !!props.node._invalid_right_error
);
</script>

<style scoped>
.rule-composer-line {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 4px 8px;
	background: #ffffff;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	transition: all 0.15s ease;
	width: 100%;
}

.rule-composer-line:hover {
	border-color: #cbd5e1;
}

.rule-composer-line.is-invalid {
	border-color: #ef4444 !important;
	background-color: #fef2f2 !important;
}

.composer-segment {
	display: flex;
	align-items: center;
}

.left-segment {
	flex: 1.2;
	min-width: 0;
}

.token-container {
	display: flex;
	align-items: center;
}

.composer-mention-trigger {
	display: flex;
	align-items: center;
	gap: 4px;
	padding: 4px 10px;
	background: #f8fafc;
	border: 1px dashed #cbd5e1;
	border-radius: 6px;
	font-size: 13px;
	color: #64748b;
	cursor: pointer;
	width: 100%;
	text-align: left;
	transition: all 0.15s ease;
}

.composer-mention-trigger:hover:not(:disabled) {
	border-color: #6366f1;
	color: #4f46e5;
	background: #eef2ff;
}

.mention-at {
	font-weight: 700;
	color: #6366f1;
}

.operator-segment {
	flex-shrink: 0;
}

.right-segment {
	flex: 1.8;
	min-width: 0;
}

.right-input-container {
	display: flex;
	align-items: center;
	gap: 4px;
	width: 100%;
}

.right-at-btn {
	padding: 2px 7px;
	border-radius: 4px;
	background: #f1f5f9;
	border: 1px solid #cbd5e1;
	font-size: 12px;
	font-weight: 700;
	color: #6366f1;
	cursor: pointer;
	transition: all 0.15s ease;
}

.right-at-btn:hover {
	background: #e0e7ff;
	border-color: #a5b4fc;
}

.preserved-draft-segment {
	display: flex;
	align-items: center;
	padding: 2px 6px;
	background: #f1f5f9;
	border-radius: 4px;
}

.action-segment {
	flex-shrink: 0;
}

.composer-remove-btn {
	border: none;
	background: transparent;
	color: #94a3b8;
	font-size: 13px;
	cursor: pointer;
	padding: 4px;
	border-radius: 4px;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.15s ease;
}

.composer-remove-btn:hover {
	color: #ef4444;
	background: #fee2e2;
}

@media (max-width: 768px) {
	.rule-composer-line {
		flex-direction: column;
		align-items: stretch;
		gap: 6px;
	}
	.left-segment,
	.right-segment {
		width: 100%;
	}
}
</style>
