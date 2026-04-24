<template>
	<div class="add-node-wrapper">
		<button ref="addBtn" class="btn btn-default btn-sm" @click="toggleMenu">
			+ {{ __("Add Node") }}
		</button>
		<div v-show="showMenu" ref="menuRef" class="node-menu">
			<div class="menu-item" @click="addNode('Process')">⚙️ {{ __("Process") }}</div>
			<div class="menu-item" @click="addNode('Condition')">◆ {{ __("Condition") }}</div>
			<div class="menu-item" @click="addNode('Stop')">■ {{ __("Stop") }}</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import { onClickOutside } from "@vueuse/core";

const emit = defineEmits(["add-node"]);

const showMenu = ref(false);
const addBtn = ref(null);
const menuRef = ref(null);

onClickOutside(addBtn, () => (showMenu.value = false), { ignore: [menuRef] });

function toggleMenu() {
	showMenu.value = !showMenu.value;
}

function addNode(type) {
	emit("add-node", type);
	showMenu.value = false;
}
</script>

<style scoped>
.add-node-wrapper {
	position: relative;
}
.node-menu {
	position: absolute;
	top: 100%;
	left: 0;
	margin-top: 4px;
	background: white;
	border: 1px solid var(--border-color);
	border-radius: 4px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	z-index: 1000;
	min-width: 150px;
}
.menu-item {
	padding: 8px 12px;
	cursor: pointer;
}
.menu-item:hover {
	background: var(--bg-light-gray);
}
</style>
