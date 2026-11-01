<template>
	<div class="collection-predicate-group border rounded p-2 mb-2 bg-light">
		<div class="collection-header d-flex align-items-center gap-2 mb-2 flex-wrap">
			<span class="badge badge-info">{{ __("COLLECTION") }}</span>

			<!-- Quantifier -->
			<select
				class="form-control form-control-sm auto-width"
				:value="node.quantifier"
				:disabled="readOnly"
				@change="onUpdateQuantifier($event.target.value)"
			>
				<option value="any">{{ __("ANY of") }}</option>
				<option value="all">{{ __("ALL of") }}</option>
				<option value="none">{{ __("NONE of") }}</option>
			</select>

			<!-- Collection Path -->
			<div class="collection-path-picker">
				<FlexValueControl
					:modelValue="node.collection"
					:docFields="docFields"
					:variableOptions="variableOptions"
					:readOnly="readOnly"
					:placeholder="__('Select collection path...')"
					@update:modelValue="onUpdateCollection"
				/>
			</div>

			<!-- Alias -->
			<div class="d-flex align-items-center gap-1">
				<span class="small text-muted">{{ __("as") }}</span>
				<input
					type="text"
					class="form-control form-control-sm alias-input"
					:value="node.alias"
					:disabled="readOnly"
					placeholder="item"
					@input="onUpdateAlias($event.target.value)"
				/>
			</div>
		</div>

		<!-- Nested predicate children slot -->
		<div class="collection-body pl-3 border-left">
			<slot></slot>
		</div>
	</div>
</template>

<script setup>
import FlexValueControl from "../../controls/FlexValueControl.vue";

const props = defineProps({
	node: {
		type: Object,
		required: true,
	},
	docFields: {
		type: Array,
		default: () => [],
	},
	variableOptions: {
		type: Array,
		default: () => [],
	},
	readOnly: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:node"]);

function onUpdateQuantifier(val) {
	emit("update:node", { ...props.node, quantifier: val });
}

function onUpdateCollection(val) {
	emit("update:node", { ...props.node, collection: val });
}

function onUpdateAlias(val) {
	emit("update:node", { ...props.node, alias: val });
}
</script>

<style scoped>
.collection-predicate-group {
	border-color: var(--fxr-border, #e5e7eb) !important;
}

.auto-width {
	width: auto;
	display: inline-block;
}

.collection-path-picker {
	min-width: 200px;
	flex: 1;
}

.alias-input {
	width: 80px;
}
</style>
