<script setup>
import { computed, inject, onMounted, provide, reactive, ref, watch } from "vue";
/**
 * CollectionUI - Child table iterator editor
 */
import ConditionNode from "./ConditionNode.vue";
import SelectControl from "../../controls/SelectControl.vue";
import DataControl from "../../controls/DataControl.vue";
import { useStore } from "../../stores";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["remove"]);

const { addCondition, addGroup, onDrop } = inject("conditionActions");
const parentVariableOptions = inject("variableOptions", ref([]));
const store = useStore();

const validationState = inject("conditionValidation", null);
const isInvalid = (field) => {
	if (!validationState || !validationState.showValidation) return false;
	return validationState.errors.some((e) => e.id === props.node.id && e.field === field);
};

const isDragOver = ref(false);

function handleDrop() {
	isDragOver.value = false;
	onDrop(props.node.where);
}

const aliasValue = computed(() => {
	const rawAlias = String(props.node.alias || "").trim();
	if (!rawAlias) return "row";
	return rawAlias.replace(/[^\w]/g, "_");
});

const scopedVariableOptions = computed(() => {
	const alias = aliasValue.value;
	const base = Array.isArray(parentVariableOptions.value) ? parentVariableOptions.value : [];
	const augmented = [...base];

	// Find the schema for the collection itself to see what sub-fields it has
	const collectionPath = props.node.collection;
	if (collectionPath) {
		const fieldMeta = props.docFields.find((f) => f.value === collectionPath);
		const isVariable = collectionPath.startsWith("vars.") || fieldMeta?.is_variable;

		if (isVariable) {
			const cleanPath = collectionPath.replace(/^vars\./, "");
			const possibleRoots = [collectionPath, `vars.${cleanPath}`, cleanPath];
			let matchedRoot = "";
			for (const root of possibleRoots) {
				const prefix = root + ".";
				if (props.docFields.some((f) => f.value.startsWith(prefix))) {
					matchedRoot = root;
					break;
				}
			}

			if (matchedRoot) {
				const prefix = matchedRoot + ".";
				props.docFields
					.filter((f) => f.value.startsWith(prefix))
					.forEach((f) => {
						const subPath = f.value.slice(prefix.length);
						augmented.unshift({
							...f,
							label: `${alias}.${subPath}`,
							value: `${alias}.${subPath}`,
							is_loop_scoped: true,
						});
					});
			}
		} else if (fieldMeta && fieldMeta.options) {
			// For standard child tables, we fetch fields for that doctype
			const childDoctype = fieldMeta.options;
			const childFields =
				typeof store.get_fields_for_doctype === "function"
					? store.get_fields_for_doctype(childDoctype, {
							alias,
							valueMode: "expression",
					  })
					: [];

			childFields.forEach((f) => {
				augmented.unshift({
					...f,
					is_loop_scoped: true,
				});
			});
		}
	}

	// Always add the root alias itself if it represents an object/row
	if (!augmented.find((v) => (v.value || v) === alias)) {
		augmented.unshift({ label: alias, value: alias, is_loop_scoped: true });
	}

	return augmented;
});

// Provide overridden alias and variable options to children
provide(
	"conditionContext",
	reactive({
		alias: computed(() => aliasValue.value),
	})
);
provide("variableOptions", scopedVariableOptions);

const tableFields = computed(() => {
	const fields = props.docFields || [];
	const validTableFields = fields.filter((f) => {
		// 1. Static Table fields
		if (f.fieldtype === "Table") return true;

		// 2. Variables marked as Table
		if (f.is_variable && f.fieldtype === "Table") return true;

		// 3. Variables that have sub-fields (schema-driven)
		if (f.is_variable) {
			const prefix = f.value + ".";
			return fields.some((sub) => sub.value.startsWith(prefix));
		}

		return false;
	});
	return validTableFields.sort((a, b) => a.label.localeCompare(b.label));
});

// Child fields for the selected table
const childDocFields = ref([]);

function addConditionForCollection() {
	const alias = aliasValue.value;
	const firstAliasField = childDocFields.value.find((f) =>
		String(f?.value || "").startsWith(`${alias}.`)
	);
	addCondition(props.node.where, alias);
	const last = props.node.where?.conditions?.[props.node.where.conditions.length - 1];
	if (last?.left && firstAliasField?.value) {
		last.left.ref = firstAliasField.value;
	}
}
// Resolve child table metadata
function fetchChildMeta() {
	const collectionPath = props.node.collection;
	const alias = aliasValue.value;

	if (!collectionPath) {
		childDocFields.value = props.docFields.filter((f) => f.fieldtype !== "Table");
		return;
	}

	// Auto-set alias from table name if not set
	if (!props.node.alias) {
		const parts = collectionPath.split(".");
		props.node.alias = parts[parts.length - 1].replace(/[^a-zA-Z0-9_]/g, "_");
	}

	// Resolve table field metadata
	const fieldMeta = props.docFields.find((f) => f.value === collectionPath);
	const isVariable = collectionPath.startsWith("vars.") || fieldMeta?.is_variable;

	if (isVariable) {
		// Try multiple possible roots for the variable (with and without vars. prefix)
		const cleanPath = collectionPath.replace(/^vars\./, "");
		const possibleRoots = [collectionPath, `vars.${cleanPath}`, cleanPath];

		let subFields = [];
		let matchedRoot = "";

		for (const root of possibleRoots) {
			const prefix = root + ".";
			const found = props.docFields.filter((f) => f.value.startsWith(prefix));
			if (found.length > 0) {
				subFields = found;
				matchedRoot = root;
				break;
			}
		}

		if (matchedRoot) {
			const prefix = matchedRoot + ".";
			const aliasFields = subFields.map((f) => {
				const subPath = f.value.slice(prefix.length);
				// Clean label: remove the variable prefix and (Variable) suffix if present
				let cleanLabel = f.label
					.replace(prefix, "")
					.replace(/\s*\([\w\u0600-\u06FF\s]+\)$/, "");

				// If cleanLabel contains a parenthesized human label, extract it
				const humanLabelMatch = cleanLabel.match(/\((.*)\)/);
				if (humanLabelMatch) {
					cleanLabel = humanLabelMatch[1];
				}

				return {
					...f,
					label: `${alias}.${subPath} (${cleanLabel})`,
					value: `${alias}.${subPath}`,
				};
			});

			// Include non-table parent fields (global context) - KEEP other variables!
			const parentFields = props.docFields.filter(
				(f) =>
					f.fieldtype !== "Table" &&
					!possibleRoots.includes(f.value) &&
					!f.value.startsWith(prefix)
			);

			const merged = [];
			const seen = new Set();
			[...aliasFields, ...parentFields].forEach((field) => {
				const key = String(field?.value || "");
				if (!key || seen.has(key)) return;
				seen.add(key);
				merged.push(field);
			});
			childDocFields.value = merged;
			return;
		}
	}

	// Find table field metadata
	// (fieldMeta is already declared above)

	if (fieldMeta && fieldMeta.options) {
		const childDoctype = fieldMeta.options;
		const getAliasFields = () =>
			typeof store.get_fields_for_doctype === "function"
				? store.get_fields_for_doctype(childDoctype, {
						alias,
						valueMode: "expression",
				  })
				: [];
		const parentFields = props.docFields.filter((f) => f.fieldtype !== "Table");
		const mergeFields = (aliasFields) => {
			const merged = [];
			const seen = new Set();
			[...(aliasFields || []), ...parentFields].forEach((field) => {
				const key = String(field?.value || "");
				if (!key || seen.has(key)) return;
				seen.add(key);
				merged.push(field);
			});
			childDocFields.value = merged;
		};

		const childFields = getAliasFields();
		if (childFields && childFields.length > 0) {
			mergeFields(childFields);
			return;
		}

		// Fetch if not cached
		if (typeof store.fetch_metadata === "function") {
			store.fetch_metadata(childDoctype).then(() => {
				mergeFields(getAliasFields());
			});
			return;
		}

		mergeFields([]);
	} else {
		childDocFields.value = props.docFields.filter((f) => f.fieldtype !== "Table");
	}
}

watch(() => props.node.collection, fetchChildMeta);
watch(() => props.node.alias, fetchChildMeta);
watch(() => props.docFields, fetchChildMeta, { deep: true });
onMounted(fetchChildMeta);
</script>

<template>
	<div class="collection-ui">
		<!-- Header -->
		<div class="collection-header">
			<!-- Logic -->
			<div class="header-col" style="width: 100px">
				<SelectControl
					v-model="node.op"
					:df="{
						label: __('Match'),
						fieldtype: 'Select',
						options: 'any\nall\nnone',
						reqd: 1,
						read_only: readOnly,
					}"
					:read_only="readOnly"
				/>
			</div>

			<!-- Table -->
			<div class="header-col flex-grow-1">
				<SelectControl
					v-model="node.collection"
					:df="{
						label: __('Table'),
						fieldtype: 'Select',
						options: tableFields,
						reqd: 1,
						read_only: readOnly,
					}"
					:invalid="isInvalid('collection')"
					:read_only="readOnly"
					@change="fetchChildMeta"
				/>
			</div>

			<!-- Alias -->
			<div class="header-col" style="width: 120px">
				<DataControl
					v-model="node.alias"
					:df="{
						label: __('Alias'),
						fieldtype: 'Data',
						placeholder: 'row',
						reqd: 1,
						read_only: readOnly,
					}"
					:read_only="readOnly"
					@update:modelValue="fetchChildMeta"
				/>
			</div>

			<!-- Actions -->
			<div class="header-col actions-col" v-if="!readOnly">
				<button
					class="fxr-btn fxr-btn--icon"
					@click="addConditionForCollection"
					:title="__('Add Condition')"
				>
					<i class="fa fa-plus"></i>
				</button>
				<button
					class="fxr-btn fxr-btn--icon"
					@click="addGroup(node.where)"
					:title="__('Add Group')"
				>
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button
					class="fxr-btn fxr-btn--icon fxr-btn--danger"
					@click="emit('remove')"
					:title="__('Remove')"
				>
					<i class="fa fa-trash-o"></i>
				</button>
			</div>
		</div>

		<!-- Nested conditions -->
		<div
			class="nested-conditions"
			:class="{ 'drag-over': isDragOver, 'is-invalid': isInvalid('where') }"
			@dragover.prevent.stop="isDragOver = true"
			@dragleave.stop="isDragOver = false"
			@drop.prevent.stop="handleDrop"
		>
			<div v-if="!node.where?.conditions?.length" class="empty-text">
				{{ __("No conditions in collection. Click + to add.") }}
			</div>
			<div
				v-for="(child, idx) in node.where?.conditions"
				:key="child.id || idx"
				class="node-wrapper"
			>
				<ConditionNode
					:node="child"
					:index="idx"
					:parentGroup="node.where"
					:docFields="childDocFields"
					:readOnly="readOnly"
				/>
			</div>
		</div>
	</div>
</template>

<style scoped>
.collection-ui {
	background: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-left: 4px solid var(--fxr-node-accent, var(--fxr-accent));
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-3);
}

.collection-header {
	display: flex;
	gap: var(--fxr-space-3);
	margin-bottom: var(--fxr-space-3);
	padding-bottom: var(--fxr-space-2);
	border-bottom: 1px solid var(--fxr-bg-muted);
}

.header-col {
	display: flex;
	flex-direction: column;
}

.actions-col {
	flex-direction: row;
	align-items: flex-end;
	gap: var(--fxr-space-1);
}

.nested-conditions {
	padding-inline-start: var(--fxr-space-4);
	border-inline-start: 2px solid var(--fxr-border);
	min-height: 20px;
	transition: all var(--fxr-transition-fast);
}

.nested-conditions.drag-over {
	background: var(--fxr-node-accent-light, var(--fxr-accent-light));
	box-shadow: inset 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
	border-radius: var(--fxr-radius-md);
}

.nested-conditions.is-invalid {
	border-color: var(--fxr-text-danger);
	background-color: var(--fxr-bg-danger);
	box-shadow: 0 0 0 2px var(--fxr-bg-danger);
}

.empty-text {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	font-style: italic;
	padding: var(--fxr-space-2) 0;
	text-align: center;
}

.node-wrapper {
	margin-bottom: 0;
}

@media (max-width: 768px) {
	.collection-ui {
		padding: var(--fxr-space-2);
	}

	.collection-header {
		flex-direction: column;
		gap: var(--fxr-space-3);
		padding-bottom: var(--fxr-space-3);
	}

	.header-col {
		width: 100% !important;
	}

	.fxr-select,
	.fxr-input {
		height: 44px;
	}

	.actions-col {
		flex-wrap: wrap;
		align-items: stretch;
		gap: var(--fxr-space-2);
	}

	.actions-col .fxr-btn {
		flex: 1;
		height: 44px;
		justify-content: center;
	}

	.actions-col .fxr-btn i {
		font-size: 16px;
	}

	.nested-conditions {
		padding-inline-start: var(--fxr-space-3);
	}
}
</style>
