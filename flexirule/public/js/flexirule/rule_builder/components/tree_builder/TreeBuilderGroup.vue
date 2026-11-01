<template>
	<div class="tree-group">
		<div class="tree-group__header">
			<div class="tree-group__logic">
				<button
					v-for="op in operators"
					:key="op"
					type="button"
					class="logic-btn"
					:class="{ active: node.operator === op }"
					:disabled="readOnly"
					@click="$emit('operator', op)"
				>
					{{ operatorLabel(op) }}
				</button>
			</div>
			<div class="tree-group__actions">
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
						:title="collectionLabel"
						:aria-label="collectionLabel"
						@click="$emit('add-collection')"
					>
						<i class="fa fa-sitemap"></i>
					</button>
				</template>
				<ActionMenu
					v-if="groupMenuActions.length"
					:actions="groupMenuActions"
					size="xs"
					:label="__('Group Actions')"
				/>
			</div>
		</div>
		<div class="tree-group__children"><slot name="children" /></div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue";
import ActionMenu from "../../controls/ActionMenu.vue";

const props = defineProps({
	node: { type: Object, required: true },
	index: { type: Number, default: 0 },
	parent: { type: Object, default: () => ({ children: [] }) },
	operators: { type: Array, default: () => ["and", "or"] },
	operatorLabel: { type: Function, default: (v) => v },
	readOnly: Boolean,
	allowGroups: Boolean,
	allowCollections: Boolean,
	collectionLabel: { type: String, default: "Collection" },
});

const emit = defineEmits([
	"operator",
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

const groupMenuActions = computed(() => {
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
.tree-group {
	width: 100%;
	min-width: 0;
	padding: var(--fxr-space-1);
	background: var(--fxr-bg-hover);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
}
.tree-group__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	flex-wrap: wrap;
	gap: var(--fxr-space-1);
	margin-bottom: var(--fxr-space-1);
}
.tree-group__logic,
.tree-group__actions {
	display: flex;
	flex-wrap: wrap;
	gap: var(--fxr-space-1);
	align-items: center;
}
.tree-group__actions .fxr-btn--icon {
	border: 1px solid var(--fxr-border-subtle);
	background: var(--fxr-surface);
	color: var(--fxr-text-secondary);
	transition: all var(--fxr-transition-fast);
}
.tree-group__actions .fxr-btn--icon:hover,
.tree-group__actions .fxr-btn--icon:focus-visible {
	border-color: var(--fxr-border-strong);
	background: var(--fxr-surface-2);
	color: var(--fxr-text-strong);
}
.logic-btn {
	border: 0;
	background: transparent;
	padding: 3px 8px;
	border-radius: var(--fxr-radius-sm);
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-bold, 700);
	color: var(--fxr-text-soft);
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast), color var(--fxr-transition-fast);
}
.logic-btn:hover:not(.active):not(:disabled) {
	background: var(--fxr-bg-muted);
	color: var(--fxr-text-strong);
}
.logic-btn:disabled {
	cursor: default;
	opacity: 0.7;
}
.logic-btn.active {
	background: var(--fxr-node-accent, var(--fxr-accent));
	color: #fff;
	box-shadow: var(--fxr-shadow-sm);
}
.tree-group__children {
	display: flex;
	flex-direction: column;
	gap: 2px;
	width: 100%;
	min-width: 0;
}
</style>
