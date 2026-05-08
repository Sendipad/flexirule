import dagre from "dagre";
import { useVueFlow } from "@vue-flow/core";

const NODE_WIDTH = 260;
const NODE_HEIGHT = 160;
const H_GAP = 100; // horizontal gap between ranks (LR) or between main and body column (TB)
const V_GAP = 120; // vertical gap between nodes

export function useRuleGraph() {
	const { nodes, edges, setNodes, setEdges, fitView } = useVueFlow();

	// ── Helpers ──────────────────────────────────────────────────────────────

	/** Collect all node IDs reachable from `startId` following only edges that
	 *  originate from `allowedSources` (or any node, if null).
	 *  Stops at `stopIds` (exclusive).  Returns a Set. */
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

	/** Find the "After Last" target of a Loop node (edge with sourceHandle === "false") */
	function getLoopAfterLastTarget(loopId, edgeList) {
		const e = edgeList.find((e) => e.source === loopId && e.sourceHandle === "false");
		return e ? e.target : null;
	}

	/** Find the "For Each" first body node (edge with sourceHandle === "default") */
	function getLoopBodyEntry(loopId, edgeList) {
		const e = edgeList.find((e) => e.source === loopId && e.sourceHandle === "default");
		return e ? e.target : null;
	}

	// ── Main layout function ──────────────────────────────────────────────────

	const layoutGraph = (direction = "TB") => {
		const currentNodes = nodes.value;
		const currentEdges = edges.value;

		const isHorizontal = direction === "LR";

		// ── 1. Identify Loop nodes and their body subgraphs ──────────────────
		const loopNodes = currentNodes.filter(
			(n) => n.type === "loop" || n.data?.action_type === "Loop"
		);

		// Map: loopId → Set of body node IDs (nodes in the For Each branch)
		const loopBodyMap = new Map();
		// Set of all body node IDs across all loops (excluded from dagre main graph)
		const allBodyNodeIds = new Set();

		loopNodes.forEach((loopNode) => {
			const afterLastId = getLoopAfterLastTarget(loopNode.id, currentEdges);
			const bodyEntryId = getLoopBodyEntry(loopNode.id, currentEdges);

			if (!bodyEntryId) return;

			// Body = all nodes reachable from bodyEntry that are NOT in the
			// "After Last" subtree (and not the loop itself)
			const afterLastSubtree = afterLastId
				? bfsReachable(afterLastId, currentEdges)
				: new Set();

			const stopSet = new Set([loopNode.id, ...afterLastSubtree]);
			const bodyIds = bfsReachable(bodyEntryId, currentEdges, stopSet);

			loopBodyMap.set(loopNode.id, { bodyIds, bodyEntryId, afterLastId });
			bodyIds.forEach((id) => allBodyNodeIds.add(id));
		});

		// ── 2. Run dagre on the MAIN FLOW (excluding body nodes) ─────────────
		const dagreGraph = new dagre.graphlib.Graph();
		dagreGraph.setDefaultEdgeLabel(() => ({}));
		dagreGraph.setGraph({
			rankdir: direction,
			nodesep: isHorizontal ? V_GAP : H_GAP,
			ranksep: isHorizontal ? H_GAP : V_GAP,
			marginx: 40,
			marginy: 40,
		});

		// Only add non-body nodes to the main dagre graph
		currentNodes.forEach((node) => {
			if (!allBodyNodeIds.has(node.id)) {
				dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
			}
		});

		// Only add edges that don't connect into the body subgraph
		currentEdges.forEach((edge) => {
			if (!allBodyNodeIds.has(edge.target) && !allBodyNodeIds.has(edge.source)) {
				// Skip the "For Each" edge (it goes into the body) for the main layout
				dagreGraph.setEdge(edge.source, edge.target);
			}
		});

		dagre.layout(dagreGraph);

		// Collect main-flow positions
		const positions = new Map();
		currentNodes.forEach((node) => {
			if (allBodyNodeIds.has(node.id)) return;
			const p = dagreGraph.node(node.id);
			if (p) {
				positions.set(node.id, {
					x: p.x - NODE_WIDTH / 2,
					y: p.y - NODE_HEIGHT / 2,
				});
			}
		});

		// ── 3. Layout each loop body in a sub-column ─────────────────────────
		loopBodyMap.forEach(({ bodyIds, bodyEntryId, afterLastId }, loopId) => {
			const loopPos = positions.get(loopId);
			if (!loopPos) return;

			// Shift AfterLast subtree out of the way to make room for body
			if (afterLastId) {
				const afterLastSubtreeIds = bfsReachable(afterLastId, currentEdges);
				const shiftX = isHorizontal ? 0 : -(NODE_WIDTH + H_GAP);
				const shiftY = isHorizontal ? -(NODE_HEIGHT + V_GAP) : 0;

				afterLastSubtreeIds.forEach((id) => {
					const p = positions.get(id);
					if (p) {
						p.x += shiftX;
						p.y += shiftY;
					}
				});
			}

			// Body nodes go straight in the direction of the flow:
			// TB: Below the loop | LR: Right of the loop
			let bodyX = loopPos.x;
			let bodyY = loopPos.y;

			if (isHorizontal) {
				bodyX += NODE_WIDTH + H_GAP;
			} else {
				bodyY += NODE_HEIGHT + V_GAP;
			}

			// BFS-order the body nodes so they stack nicely
			const ordered = [];
			const visited = new Set();
			const queue = [bodyEntryId];
			while (queue.length) {
				const id = queue.shift();
				if (visited.has(id) || !bodyIds.has(id)) continue;
				visited.add(id);
				ordered.push(id);
				currentEdges.forEach((e) => {
					if (e.source === id && bodyIds.has(e.target) && !visited.has(e.target)) {
						queue.push(e.target);
					}
				});
			}

			// Assign positions stacked in the body sub-column
			ordered.forEach((id, i) => {
				if (isHorizontal) {
					positions.set(id, {
						x: bodyX + (NODE_WIDTH + H_GAP) * i,
						y: bodyY,
					});
				} else {
					positions.set(id, {
						x: bodyX,
						y: bodyY + (NODE_HEIGHT + V_GAP) * i,
					});
				}
			});
		});

		// ── 4. Apply positions back to nodes ─────────────────────────────────
		// Identify the "last" node in each loop body (the one that should return)
		const loopReturnSourceIds = new Set();
		loopBodyMap.forEach(({ bodyIds, bodyEntryId }, loopId) => {
			bodyIds.forEach((id) => {
				const hasChildrenInBody = currentEdges.some(
					(e) => e.source === id && bodyIds.has(e.target)
				);
				if (!hasChildrenInBody) {
					loopReturnSourceIds.add(id);
				}
			});
		});

		const layoutedNodes = currentNodes.map((node) => {
			const pos = positions.get(node.id) || node.position;
			const isReturnNode = loopReturnSourceIds.has(node.id);

			return {
				...node,
				position: pos,
				sourcePosition: isReturnNode
					? isHorizontal
						? "bottom"
						: "right" // Side exit for return path
					: isHorizontal
					? "right"
					: "bottom", // Standard flow exit
				targetPosition: isHorizontal ? "left" : "top",
			};
		});

		setNodes(layoutedNodes);

		setTimeout(() => {
			fitView({ padding: 0.2, duration: 500 });
		}, 100);
	};

	return { layoutGraph };
}
