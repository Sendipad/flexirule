<template>
	<div
		class="tree-leaf"
		:class="{
			'is-editing': isEditing,
			'is-summary-mode': inlinePresentation.presentation === 'summary',
			'is-editor-mode': inlinePresentation.presentation === 'editor',
			'is-read-only': readOnly,
			'has-context-edit': canEditInReadOnly,
		}"
	>
		<div
			v-if="inlinePresentation.presentation === 'summary'"
			class="tree-leaf__summary"
			:class="{ 'is-toggleable': inlinePresentation.canToggle && !readOnly }"
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
					v-if="canEditInReadOnly"
					type="button"
					class="tree-leaf__action tree-leaf__context-edit"
					:title="__('Edit')"
					:aria-label="__('Edit')"
					@click.stop.prevent="startEditing"
				>
					<i class="fa fa-pencil" aria-hidden="true"></i>
				</button>
				<ActionMenu
					v-if="leafMenuActions.length"
					:actions="leafMenuActions"
					size="xs"
					:label="__('Leaf Actions')"
				/>
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
						@click.stop.prevent="stopEditing"
					>
						<i class="fa fa-check" aria-hidden="true"></i>
					</button>
					<ActionMenu
						v-if="leafMenuActions.length"
						:actions="leafMenuActions"
						size="xs"
						:label="__('Leaf Actions')"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, useSlots } from "vue";
import {
	getInlinePresentation,
	resolvePresentationMode,
} from "../../controls/inline_presentation_policy.mjs";
import ActionMenu from "../../controls/ActionMenu.vue";

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

const emit = defineEmits(["remove", "move-up", "move-down", "select"]);

const api = inject("treeBuilderContext", null);
const slots = useSlots();

const hasSummarySlot = computed(() =>
	api ? Boolean(api.hasSummarySlot?.value) : Boolean(slots["leaf-summary"])
);

const isEditing = computed(() => {
	const editingId = api?.editingNodeId?.value ?? api?.editingNodeId;
	return editingId === props.node.id;
});

const canEditRule = computed(() => {
	const val = api?.canEdit?.value ?? api?.canEdit;
	return Boolean(val);
});

const canEditInReadOnly = computed(() => {
	return Boolean(props.readOnly && canEditRule.value && inlinePresentation.value.canToggle);
});

const isTransientNew = computed(() => {
	if (typeof api?.isTransientNew === "function") {
		return api.isTransientNew(props.node.id);
	}
	return false;
});

const isNew = computed(() => {
	if (isTransientNew.value) return true;
	if (typeof props.isLeafNew === "function") return props.isLeafNew(props.node);
	if (typeof api?.isLeafNew?.value === "function") return api.isLeafNew.value(props.node);
	return Boolean(props.node?.isNew);
});

const isValid = computed(() => {
	if (typeof props.isLeafValid === "function") return props.isLeafValid(props.node);
	if (typeof api?.isLeafValid?.value === "function") return api.isLeafValid.value(props.node);
	return props.node?.isValid !== false;
});

const resolvedPresentationMode = computed(() =>
	resolvePresentationMode(props.presentationMode || api?.presentationMode?.value)
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
	if (mode === "hybrid") return isEditing.value && isValid.value;
	return false;
});

const isFirst = computed(() => props.index <= 0);
const isLast = computed(() => {
	const count = props.parent?.children?.length ?? 0;
	return props.index >= count - 1;
});

const leafMenuActions = computed(() => {
	const items = [];

	if (inlinePresentation.value.presentation === "summary") {
		if (inlinePresentation.value.canToggle && (!props.readOnly || canEditRule.value)) {
			items.push({
				id: "edit",
				label: __("Edit"),
				icon: "fa fa-pencil",
				onClick: () => {
					startEditing();
				},
			});
		}
	} else if (inlinePresentation.value.presentation === "editor") {
		if (canFinishEditing.value) {
			items.push({
				id: "finish",
				label: __("Finish editing"),
				icon: "fa fa-check",
				onClick: () => {
					stopEditing();
				},
			});
		}
	}

	if (typeof api?.selectNode === "function") {
		items.push({
			id: "select",
			label: __("Select"),
			icon: "fa fa-mouse-pointer",
			onClick: () => {
				api.selectNode(props.node.id);
				emit("select", props.node.id);
			},
		});
	}

	if (!props.readOnly) {
		items.push({
			id: "move-up",
			label: __("Move up"),
			icon: "fa fa-arrow-up",
			disabled: isFirst.value,
			onClick: () => {
				if (typeof api?.moveNodeUp === "function") {
					api.moveNodeUp(props.node.id);
				}
				emit("move-up", props.node.id);
			},
		});

		items.push({
			id: "move-down",
			label: __("Move down"),
			icon: "fa fa-arrow-down",
			disabled: isLast.value,
			onClick: () => {
				if (typeof api?.moveNodeDown === "function") {
					api.moveNodeDown(props.node.id);
				}
				emit("move-down", props.node.id);
			},
		});

		items.push({
			id: "delete",
			label: __("Delete"),
			icon: "fa fa-trash",
			danger: true,
			onClick: () => {
				emit("remove");
			},
		});
	}

	return items;
});

function startEditing() {
	if (props.readOnly && !canEditRule.value) return;
	if (typeof api?.setEditing === "function") {
		api.setEditing(props.node.id);
	}
}

function stopEditing() {
	if (typeof api?.finishEditing === "function") {
		api.finishEditing(props.node.id);
	} else if (typeof api?.setEditing === "function") {
		const editingId = api?.editingNodeId?.value ?? api?.editingNodeId;
		if (editingId === props.node.id) {
			api.setEditing(null);
		}
	}
}

function onDoubleClickSummary(event) {
	if (props.readOnly && !canEditRule.value) return;
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
	position: relative;
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
	width: 26px;
	min-width: 26px;
	height: 26px;
	margin: 0;
	padding: 0;
	border: 1px solid transparent;
	border-radius: var(--fxr-radius-md, 6px);
	background: transparent;
	color: var(--fxr-text-secondary, #4b5563);
	cursor: pointer;
	transition: opacity 120ms ease, background-color 120ms ease, border-color 120ms ease,
		color 120ms ease;
}

.tree-leaf__action:hover,
.tree-leaf__action:focus-visible {
	border-color: var(--fxr-border, #d1d5db);
	background: var(--fxr-bg-muted, #f3f4f6);
	color: var(--fxr-text, #111827);
}

.tree-leaf__context-edit {
	opacity: 0;
	pointer-events: none;
}

.tree-leaf.has-context-edit:hover .tree-leaf__context-edit,
.tree-leaf.has-context-edit:focus-within .tree-leaf__context-edit,
.tree-leaf__context-edit:hover,
.tree-leaf__context-edit:focus-visible {
	opacity: 1;
	pointer-events: auto;
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
