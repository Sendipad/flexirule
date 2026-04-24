import { ref, watch } from "vue";
/**
 * useConditionTree - Logic for managing condition group state
 */

function get_uuid() {
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
		var r = (Math.random() * 16) | 0,
			v = c == "x" ? r : (r & 0x3) | 0x8;
		return v.toString(16);
	});
}

export function useConditionTree(props, emit) {
	const root = ref(props.modelValue || { op: "and", conditions: [] });

	// Ensure all nodes have IDs recursively
	const _ensureIds = (nodes) => {
		if (!nodes) return;
		nodes.forEach((node) => {
			if (!node.id) node.id = get_uuid();
			if (node.conditions) _ensureIds(node.conditions);
			if (node.where?.conditions) _ensureIds(node.where.conditions);
		});
	};

	watch(
		() => props.modelValue,
		(val) => {
			if (val) {
				_ensureIds(val.conditions);
				root.value = val;
			}
		},
		{ immediate: true, deep: true }
	);

	watch(
		root,
		(val) => {
			emit("update:modelValue", val);
		},
		{ deep: true }
	);

	const initializeModel = () => {
		root.value = { op: "and", conditions: [] };
	};

	const addCondition = (group, defaultRef = "") => {
		if (!group.conditions) group.conditions = [];
		group.conditions.push({
			id: get_uuid(),
			left: { ref: defaultRef },
			op: "==",
			right: { value: "" },
		});
	};

	const addGroup = (group) => {
		if (!group.conditions) group.conditions = [];
		group.conditions.push({
			id: get_uuid(),
			op: "and",
			conditions: [],
		});
	};

	const addCollection = (group) => {
		if (!group.conditions) group.conditions = [];
		group.conditions.push({
			id: get_uuid(),
			op: "any",
			collection: "",
			alias: "row",
			where: {
				op: "and",
				conditions: [],
			},
		});
	};

	const removeNode = (group, index) => {
		group.conditions.splice(index, 1);
	};

	return {
		root,
		initializeModel,
		addCondition,
		addGroup,
		addCollection,
		removeNode,
	};
}
