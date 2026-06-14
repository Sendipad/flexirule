<script setup>
import { ref, nextTick } from "vue";

const props = defineProps({
	value: {
		type: String,
		default: "",
	},
	isReadOnly: {
		type: Boolean,
		default: false,
	},
	tag: {
		type: String,
		default: "div",
	},
});

const emit = defineEmits(["update:value"]);

const isEditing = ref(false);
const editValue = ref(props.value);
const inputRef = ref(null);

async function startEditing() {
	if (props.isReadOnly) return;
	isEditing.value = true;
	editValue.value = props.value;
	await nextTick();
	inputRef.value?.focus();
	inputRef.value?.select();
}

function stopEditing() {
	if (!isEditing.value) return;
	isEditing.value = false;
	if (editValue.value !== props.value) {
		emit("update:value", editValue.value);
	}
}

function handleKeydown(e) {
	if (e.key === "Enter") {
		stopEditing();
	} else if (e.key === "Escape") {
		editValue.value = props.value;
		isEditing.value = false;
	}
}
</script>

<template>
	<div class="inline-editor" @dblclick.stop="startEditing">
		<template v-if="isEditing">
			<input
				ref="inputRef"
				v-model="editValue"
				class="edit-input"
				@blur="stopEditing"
				@keydown="handleKeydown"
				@click.stop
			/>
		</template>
		<template v-else>
			<component :is="tag" class="display-text">
				<slot>{{ value }}</slot>
			</component>
		</template>
	</div>
</template>

<style scoped>
.inline-editor {
	display: inline-block;
	width: 100%;
	cursor: text;
}

.edit-input {
	width: 100%;
	border: 1px solid var(--fxr-accent);
	border-radius: 4px;
	padding: 2px 4px;
	font-size: inherit;
	font-weight: inherit;
	color: var(--fxr-text-strong);
	background: var(--fxr-bg-input);
	outline: none;
	box-shadow: 0 0 0 2px var(--fxr-accent-soft);
}

.display-text {
	width: 100%;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
</style>
