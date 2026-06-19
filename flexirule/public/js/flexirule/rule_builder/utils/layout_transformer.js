/**
 * Layout Transformer Utility
 * Handles coordinate projection between Vertical (TB) and Horizontal (LR) orientations.
 */

const NODE_WIDTH = 220;
const NODE_HEIGHT = 140;

// Spacing constants from useRuleGraph.js
const H_GAP = 46;
const V_GAP = 72;

// Scaling factors to preserve relative spacing when rotating non-square nodes
const S_RANK = (NODE_WIDTH + V_GAP) / (NODE_HEIGHT + V_GAP); // ~1.377
const S_SIB = (NODE_HEIGHT + H_GAP) / (NODE_WIDTH + H_GAP); // ~0.699

/**
 * Projects nodes and handles into a new orientation without modifying source data.
 */
export function projectGraph(nodes, edges, direction = "TB") {
	if (direction === "TB" || !direction) {
		return nodes.map((n) => ({
			...n,
			sourcePosition: n.sourcePosition || "bottom",
			targetPosition: n.targetPosition || "top",
		}));
	}

	const isHorizontal = direction === "LR";
	const loopReturnIds = identifyLoopReturnNodes(nodes, edges);

	return nodes.map((node) => {
		const { x, y } = node.position;

		// Calculate center in TB (assuming input is always TB)
		const cx = x + NODE_WIDTH / 2;
		const cy = y + NODE_HEIGHT / 2;

		// Project to LR: TB Y maps to LR X, TB X maps to LR Y
		const ncx = cy * S_RANK;
		const ncy = cx * S_SIB;

		const isReturnNode = loopReturnIds.has(node.id);

		return {
			...node,
			position: {
				x: Math.round(ncx - NODE_WIDTH / 2),
				y: Math.round(ncy - NODE_HEIGHT / 2),
			},
			isHorizontal: true,
			sourcePosition: isReturnNode
				? isHorizontal
					? "top"
					: "left"
				: isHorizontal
				? "right"
				: "bottom",
			targetPosition: isHorizontal ? "left" : "top",
		};
	});
}

/**
 * Detection logic for return nodes (nodes at the end of a loop body)
 * Matches the logic in useRuleGraph.js to ensure consistent routing.
 */
function identifyLoopReturnNodes(nodes, edges) {
	const loopReturnSourceIds = new Set();
	const loopNodes = nodes.filter((n) => n.type === "loop" || n.data?.action_type === "Loop");

	const loopBodyMap = new Map();
	loopNodes.forEach((loopNode) => {
		const bodyEntryEdge = edges.find(
			(e) => e.source === loopNode.id && e.sourceHandle === "default"
		);
		const afterLastEdge = edges.find(
			(e) => e.source === loopNode.id && e.sourceHandle === "false"
		);

		if (!bodyEntryEdge) return;

		const bodyEntryId = bodyEntryEdge.target;
		const afterLastId = afterLastEdge?.target;

		const afterLastSubtree = afterLastId ? bfsReachable(afterLastId, edges) : new Set();
		const stopSet = new Set([loopNode.id, ...afterLastSubtree]);
		const bodyIds = bfsReachable(bodyEntryId, edges, stopSet);

		bodyIds.forEach((id) => {
			const hasChildrenInBody = edges.some((e) => e.source === id && bodyIds.has(e.target));
			if (!hasChildrenInBody) {
				loopReturnSourceIds.add(id);
			}
		});
	});

	return loopReturnSourceIds;
}

function bfsReachable(startId, edgeList, stopIds = new Set()) {
	const visited = new Set();
	const queue = [startId];
	while (queue.length) {
		const id = queue.shift();
		if (visited.has(id) || stopIds.has(id)) continue;
		visited.add(id);
		edgeList.forEach((e) => {
			if (e.source === id && !visited.has(e.target) && !stopIds.has(e.target)) {
				queue.push(e.target);
			}
		});
	}
	return visited;
}
