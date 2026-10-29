<template>
	<div class="tree-collection" :class="{ 'has-contextual-edit': readOnly && canEditRule }">
		<div class="tree-collection__header">
			<div class="tree-collection__label">
				<i class="fa fa-sitemap"></i>
				<span
					><slot name="label" :node="node"
						><strong>{{ label }}</strong></slot
					></span
				>
			</div>
			<div class="tree-collection__actions">
				<button
					v-if="!readOnly"
					type="button"
					class="fxr-btn fxr-btn--icon"
					:title="__('Add Leaf')"
					@click="$emit('add-leaf')"
				>
					<i class="fa fa-plus"></i>
				</button>
				<button
					v-if="!readOnly && allowGroups"
					type="button"
					class="fxr-btn fxr-btn--icon"
					:title="__('Add Group')"
					@click="$emit('add-group')"
				>
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button
					v-if="!readOnly && allowCollections"
					type="button"
					class="fxr-btn fxr-btn--icon"
					:title="label"
					@click="$emit('add-collection')"
				>
					<i class="fa fa-sitemap"></i>
				</button>
				<button
					v-if="readOnly && canEditRule"
					type="button"
					class="fxr-btn fxr-btn--icon tree-contextual-edit-btn"
					:title="__('Edit')"
					:aria-label="__('Edit')"
					@click="$emit('edit')"
				>
					<i class="fa fa-pencil" aria-hidden="true"></i>
				</button>
				<ActionMenu
					v-if="!readOnly"
					:items="menuItems"
					:buttonAriaLabel="__('Collection Actions')"
				/>
			</div>
		</div>
		<div class="tree-collection__children"><slot name="children" /></div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import ActionMenu from "../ActionMenu.vue";

const props = defineProps({
	node: { type: Object, required: true },
	label: { type: String, default: "Collection" },
	readOnly: Boolean,
	canEditRule: Boolean,
	allowGroups: Boolean,
	allowCollections: Boolean,
	isFirstSibling: Boolean,
	isLastSibling: Boolean,
});

const emit = defineEmits([
	"add-leaf",
	"add-group",
	"add-collection",
	"remove",
	"select",
	"edit",
	"move-up",
	"move-down",
]);

const menuItems = computed(() => [
	{ id: "edit", label: __("Edit"), icon: "fa fa-pencil", handler: () => emit("edit") },
	{
		id: "select",
		label: __("Select"),
		icon: "fa fa-mouse-pointer",
		handler: () => emit("select"),
	},
	{
		id: "move-up",
		label: __("Move up"),
		icon: "fa fa-chevron-up",
		disabled: props.isFirstSibling,
		handler: () => emit("move-up"),
	},
	{
		id: "move-down",
		label: __("Move down"),
		icon: "fa fa-chevron-down",
		disabled: props.isLastSibling,
		handler: () => emit("move-down"),
	},
	{
		id: "delete",
		label: __("Delete"),
		icon: "fa fa-trash",
		danger: true,
		handler: () => emit("remove"),
	},
]);
</script>

<style scoped>
.tree-collection {
	position: relative;
	padding: var(--fxr-space-2);
	border: 1px solid var(--fxr-border-subtle);
	border-left: 3px solid var(--fxr-node-accent, var(--fxr-accent));
	border-radius: var(--fxr-radius-lg);
	background: var(--fxr-surface);
}

.tree-collection.has-contextual-edit .tree-contextual-edit-btn {
	opacity: 0;
	transition: opacity var(--fxr-transition-fast, 120ms ease);
}

.tree-collection.has-contextual-edit:hover .tree-contextual-edit-btn,
.tree-collection.has-contextual-edit:focus-within .tree-contextual-edit-btn {
	opacity: 1;
}

.tree-collection__header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: var(--fxr-space-2);
	margin-bottom: var(--fxr-space-2);
}

.tree-collection__label,
.tree-collection__actions {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: var(--fxr-space-1);
}

.tree-collection__actions .fxr-btn--icon {
	border: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface);
	color: var(--fxr-text-secondary);
	transition: all var(--fxr-transition-fast);
}

.tree-collection__actions .fxr-btn--icon:hover,
.tree-collection__actions .fxr-btn--icon:focus-visible {
	border-color: var(--fxr-border-strong);
	background: var(--fxr-surface-2);
	color: var(--fxr-text-strong);
}

.tree-collection__children {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1);
	width: 100%;
	min-width: 0;
}
</style>
