export function createId() {
	if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
		return crypto.randomUUID();
	}
	return "tree-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
}

export function cloneTree(value) {
	if (value === undefined || value === null) return value;
	return JSON.parse(JSON.stringify(value));
}

export function isGroupNode(node) {
	return !!node && node.type === "group";
}

export function isLeafNode(node) {
	return !!node && node.type === "leaf";
}

export function normalizeTree(value) {
	if (!value || typeof value !== "object") {
		return { id: createId(), type: "group", operator: "and", children: [] };
	}

	if (value.type === "group") {
		return {
			id: value.id || createId(),
			type: "group",
			operator: value.operator || "and",
			children: Array.isArray(value.children)
				? value.children.map(normalizeTree).filter(Boolean)
				: [],
		};
	}

	return {
		id: value.id || createId(),
		type: "leaf",
		...cloneTree(value),
	};
}

export function isDescendant(node, targetId) {
	if (!node || !targetId) return false;
	if (node.id === targetId) return true;
	if (isGroupNode(node)) return (node.children || []).some((child) => isDescendant(child, targetId));
	return false;
}
