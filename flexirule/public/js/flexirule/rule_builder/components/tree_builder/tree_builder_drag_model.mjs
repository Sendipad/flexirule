/**
 * Resolve an edge drop to a sibling insertion position.
 * The invisible edge hit zones deliberately map to the same parent/index
 * contract as the existing TreeBuilder move commands.
 */
export function getSiblingDropIntent(parentId, index, position) {
	if (!parentId || !Number.isInteger(index) || index < 0) return null;
	if (position !== "before" && position !== "after") return null;

	return {
		targetId: parentId,
		position: index + (position === "after" ? 1 : 0),
		visualPosition: position,
	};
}
