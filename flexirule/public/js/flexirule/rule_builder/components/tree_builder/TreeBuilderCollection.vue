<template>
	<div class="tree-collection">
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
				<template v-if="!readOnly">
					<button
						type="button"
						class="fxr-btn fxr-btn--icon"
						:title="__('Add Condition')"
						:aria-label="__('Add Condition')"
						@click="$emit('add-leaf')"
					>
						<i class="fa fa-plus"></i>
					</button>
					<button
						v-if="allowGroups"
						type="button"
						class="fxr-btn fxr-btn--icon"
						:title="__('Add Group')"
						:aria-label="__('Add Group')"
						@click="$emit('add-group')"
					>
						<i class="fa fa-folder-open-o"></i>
					</button>
					<button
						v-if="allowCollections"
						type="button"
						class="fxr-btn fxr-btn--icon"
						:title="__('Add Collection')"
						:aria-label="__('Add Collection')"
						@click="$emit('add-collection')"
					>
						<i class="fa fa-sitemap"></i>
					</button>
				</template>
				<ActionMenu
					v-if="collectionMenuActions.length"
					:actions="collectionMenuActions"
					size="xs"
					:label="__('Collection Actions')"
				/>
			</div>
		</div>
		<div class="tree-collection__children"><slot name="children" /></div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue";
import ActionMenu from "../../controls/ActionMenu.vue";

const props = defineProps({
	node: { type: Object, required: true },
	index: { type: Number, default: 0 },
	parent: { type: Object, default: () => ({ children: [] }) },
	label: { type: String, default: "Collection" },
	readOnly: Boolean,
	allowGroups: Boolean,
	allowCollections: Boolean,
});

const emit = defineEmits([
	"add-leaf",
	"add-group",
	"add-collection",
	"remove",
	"move-up",
	"move-down",
	"select",
]);

const api = inject("treeBuilderContext", null);

const isFirst = computed(() => props.index <= 0);
const isLast = computed(() => {
	const count = props.parent?.children?.length ?? 0;
	return props.index >= count - 1;
});

const collectionMenuActions = computed(() => {
	if (props.readOnly) return [];
	const items = [];

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

	return items;
});
</script>

<style scoped>
.tree-collection {
	padding: var(--fxr-space-2);
	border: 1px solid var(--fxr-border-subtle);
	border-left: 3px solid var(--fxr-node-accent, var(--fxr-accent));
	border-radius: var(--fxr-radius-lg);
	background: var(--fxr-surface);
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
