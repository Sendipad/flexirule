<template>
	<div
		class="tree-leaf"
		:class="{
			'is-editing': isEditing,
			'is-summary-mode': inlinePresentation.presentation === 'summary',
			'is-editor-mode': inlinePresentation.presentation === 'editor',
		}"
	>
		<div
			v-if="inlinePresentation.presentation === 'summary'"
			class="tree-leaf__summary"
			:class="{ 'is-toggleable': inlinePresentation.canToggle }"
			@dblclick="onDoubleClickSummary"
		>
			<div class="tree-leaf__summary-content">
				<slot
					name="leaf-summary"
					:node="node"
					:context="context"
					:index="index"
					:parent="parent"
					:readOnly="readOnly"
					:isEditing="isEditing"
				/>
			</div>
			<div class="tree-leaf__actions">
				<button
					v-if="inlinePresentation.canToggle"
					type="button"
					class="tree-leaf__action tree-leaf__edit"
					:title="__('Edit')"
					:aria-label="__('Edit')"
					@click="startEditing"
				>
					<i class="fa fa-pencil" aria-hidden="true"></i>
				</button>
				<button
					v-if="!readOnly"
					type="button"
					class="tree-leaf__action tree-leaf__remove"
					:title="__('Remove')"
					:aria-label="__('Remove')"
					@click="$emit('remove')"
				>
					<i class="fa fa-trash" aria-hidden="true"></i>
				</button>
			</div>
		</div>

		<div v-else class="tree-leaf__editor-wrapper">
			<div
				v-if="resolvedEditorLayout === 'alongside' && hasSummarySlot"
				class="tree-leaf__summary tree-leaf__summary--alongside"
			>
				<slot
					name="leaf-summary"
					:node="node"
					:context="context"
					:index="index"
					:parent="parent"
					:readOnly="readOnly"
					:isEditing="isEditing"
				/>
			</div>
			<div class="tree-leaf__editor">
				<div class="tree-leaf__content">
					<slot
						:node="node"
						:context="context"
						:index="index"
						:parent="parent"
						:readOnly="readOnly"
						:isEditing="isEditing"
					/>
				</div>
				<div class="tree-leaf__actions">
					<button
						v-if="canFinishEditing"
						type="button"
						class="tree-leaf__action tree-leaf__finish"
						:title="__('Finish editing / Show summary')"
						:aria-label="__('Finish editing / Show summary')"
						@click="stopEditing"
					>
						<i class="fa fa-check" aria-hidden="true"></i>
					</button>
					<button
						v-if="!readOnly"
						type="button"
						class="tree-leaf__action tree-leaf__remove"
						:title="__('Remove')"
						:aria-label="__('Remove')"
						@click="$emit('remove')"
					>
						<i class="fa fa-trash" aria-hidden="true"></i>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, useSlots } from "vue";
import { getInlinePresentation } from "../../controls/inline_presentation_policy.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	context: { type: Object, default: () => ({ scopes: [], path: [] }) },
	index: { type: Number, required: true },
	parent: { type: Object, required: true },
	readOnly: Boolean,
	presentationMode: { type: String, default: undefined },
	editorLayout: { type: String, default: undefined },
	isLeafNew: { type: Function, default: undefined },
	isLeafValid: { type: Function, default: undefined },
});

defineEmits(["remove"]);

const api = inject("treeBuilderContext", null);
const slots = useSlots();

const hasSummarySlot = computed(() =>
	api ? Boolean(api.hasSummarySlot?.value) : Boolean(slots["leaf-summary"])
);

const isEditing = computed(() => {
	const editingId = api?.editingNodeId?.value ?? api?.editingNodeId;
	return editingId === props.node.id;
});

const isNew = computed(() => {
	if (typeof props.isLeafNew === "function") return props.isLeafNew(props.node);
	if (typeof api?.isLeafNew?.value === "function") return api.isLeafNew.value(props.node);
	return Boolean(props.node?.isNew);
});

const isValid = computed(() => {
	if (typeof props.isLeafValid === "function") return props.isLeafValid(props.node);
	if (typeof api?.isLeafValid?.value === "function") return api.isLeafValid.value(props.node);
	return props.node?.isValid !== false;
});

const resolvedPresentationMode = computed(
	() => props.presentationMode || api?.presentationMode?.value || "hybrid"
);

const resolvedEditorLayout = computed(
	() => props.editorLayout || api?.editorLayout?.value || "replace"
);

const inlinePresentation = computed(() =>
	getInlinePresentation({
		mode: resolvedPresentationMode.value,
		isNew: isNew.value,
		isValid: isValid.value,
		isEditing: isEditing.value,
		readOnly: props.readOnly,
		hasSummary: hasSummarySlot.value,
	})
);

const canFinishEditing = computed(() => {
	if (!hasSummarySlot.value || !inlinePresentation.value.canToggle) return false;
	const mode = resolvedPresentationMode.value;
	if (mode === "summary") return isEditing.value;
	if (mode === "hybrid") return isEditing.value && !isNew.value && isValid.value;
	return false;
});

function startEditing() {
	if (props.readOnly) return;
	if (typeof api?.setEditing === "function") {
		api.setEditing(props.node.id);
	}
}

function stopEditing() {
	if (typeof api?.setEditing === "function") {
		const editingId = api?.editingNodeId?.value ?? api?.editingNodeId;
		if (editingId === props.node.id) {
			api.setEditing(null);
		}
	}
}

function onDoubleClickSummary(event) {
	if (!inlinePresentation.value.canToggle) return;
	const target = event.target;
	if (
		target instanceof Element &&
		target.closest(
			"a, button, input, select, textarea, [contenteditable='true'], [role='button'], [role='combobox']"
		)
	) {
		return;
	}
	startEditing();
}
</script>

<style scoped>
.tree-leaf {
	width: 100%;
	min-width: 0;
	cursor: grab;
}

.tree-leaf.is-dragging {
	cursor: grabbing;
	opacity: 0.82;
}

.tree-leaf__summary,
.tree-leaf__editor {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: var(--fxr-space-1, 4px);
	align-items: center;
	width: 100%;
	min-width: 0;
}

.tree-leaf__summary.is-toggleable {
	cursor: pointer;
}

.tree-leaf__summary-content,
.tree-leaf__content {
	width: 100%;
	min-width: 0;
}

.tree-leaf__summary--alongside {
	margin-bottom: var(--fxr-space-1, 4px);
	padding-bottom: var(--fxr-space-1, 4px);
	border-bottom: 1px dashed var(--fxr-border-subtle, #e5e7eb);
}

.tree-leaf__actions {
	display: flex;
	align-items: center;
	gap: 2px;
}

.tree-leaf__action {
	display: inline-flex;
	align-self: center;
	align-items: center;
	justify-content: center;
	width: 28px;
	min-width: 28px;
	height: var(--fxr-input-height, 32px);
	margin: 0;
	padding: 0;
	border: 1px solid transparent;
	border-radius: var(--fxr-radius-md, 6px);
	background: transparent;
	color: var(--fxr-text-secondary, #4b5563);
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast, 120ms ease),
		border-color var(--fxr-transition-fast, 120ms ease),
		color var(--fxr-transition-fast, 120ms ease);
}

.tree-leaf__action:hover,
.tree-leaf__action:focus-visible {
	border-color: var(--fxr-border, #d1d5db);
	background: var(--fxr-bg-muted, #f3f4f6);
	color: var(--fxr-text, #111827);
}

.tree-leaf__remove {
	color: var(--fxr-text-danger, #dc2626);
}

.tree-leaf__remove:hover,
.tree-leaf__remove:focus-visible {
	border-color: var(--fxr-border-danger, #dc2626);
	background: var(--fxr-bg-danger, #fef2f2);
	color: var(--fxr-text-danger, #dc2626);
}

.tree-leaf__finish {
	color: var(--fxr-accent, #2563eb);
}

.tree-leaf__finish:hover,
.tree-leaf__finish:focus-visible {
	border-color: var(--fxr-border-focus, #3b82f6);
	background: var(--fxr-accent-soft, #eff6ff);
	color: var(--fxr-accent, #2563eb);
}
</style>
