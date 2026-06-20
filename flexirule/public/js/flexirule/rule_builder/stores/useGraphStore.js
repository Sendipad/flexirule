/**
 * useGraphStore — Nodes, edges, topology, and graph operations.
 *
 * Follows Frappe builder pattern (workflow_builder: elements + node/edge ops):
 *   - Owns the visual graph state (nodes, edges)
 *   - Provides graph operations: add, delete, touch, topology
 *   - Sync logic: actions ↔ graph, merge visual layout
 *   - No knowledge of Rule document lifecycle (that's useRuleStore)
 *
 * Extracted from store.js lines: 15-16, 261-394, 427-736, 1223-1434
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { deepClone } from "../utils/serialization";
import {
	getContract,
	getEffectiveActionPolicy,
	getOperationOptions,
	getProcessOperationDefinition,
	normalizeActionType,
	isTerminalAction,
	ACTION_TYPES_WITH_REFERENCE_CONTEXT,
	ACTION_TYPES_WITH_RETURN_SCHEMA,
} from "../../core/contracts";
import { mapActionTypeToNodeType } from "../composables/useActionTypeMapper";
import { getConditionPayload } from "../utils/condition_payload";
import { generateShortId } from "../utils/schema_utils.js";

export const useGraphStore = defineStore("rule-builder-graph", () => {
	// ── Core graph state ──
	const nodes = ref([]);
	const edges = ref([]);

	// ── Cascade disable computed ──
	// BFS from start node: any node not reachable via enabled path is "effectively disabled"
	const effectiveDisabledIds = computed(() => {
		const disabledSet = new Set();
		const nodeMap = new Map(nodes.value.map((n) => [n.id, n]));
		const adj = new Map();

		edges.value.forEach((e) => {
			if (!adj.has(e.source)) adj.set(e.source, []);
			adj.get(e.source).push(e.target);
		});

		const visited = new Set();
		const queue = ["start"];

		while (queue.length > 0) {
			const currentId = queue.shift();
			if (visited.has(currentId)) continue;

			const node = nodeMap.get(currentId);
			if (currentId !== "start" && node?.data?.is_enabled === 0) {
				continue;
			}

			visited.add(currentId);
			const children = adj.get(currentId) || [];
			children.forEach((childId) => {
				if (!visited.has(childId)) queue.push(childId);
			});
		}

		nodes.value.forEach((n) => {
			if (!visited.has(n.id)) disabledSet.add(n.id);
		});

		return disabledSet;
	});

	function getEffectivelyDisabledIds() {
		return effectiveDisabledIds.value;
	}

	// ── Snapshot for dirty checking + history ──
	/**
	 * Returns a stable, serializable representation of the graph data.
	 * Excludes transient UI state (selection, dragging, etc.) to ensure
	 * comparison only detects meaningful changes.
	 */
	function getStateSnapshot() {
		const nodesSnap = nodes.value.map((el) => {
			// Deep clone data to avoid reference pollution
			const data = deepClone(el.data || {});
			return {
				id: el.id,
				type: el.type,
				label: el.label,
				data: data,
				position: {
					x: Math.round(el.position?.x || 0),
					y: Math.round(el.position?.y || 0),
				},
			};
		});
		const edgesSnap = edges.value.map((el) => ({
			id: el.id,
			source: el.source,
			target: el.target,
			sourceHandle: el.sourceHandle || "default",
			targetHandle: el.targetHandle || null,
		}));

		// Return a flat array to maintain compatibility with existing logic
		return [...nodesSnap, ...edgesSnap].sort((a, b) => (a.id || "").localeCompare(b.id || ""));
	}

	function getGraphSnapshot() {
		// Use the stable state snapshot for history to prevent transient UI changes
		// (like node selection or dragging) from polluting the undo/redo stack.
		return getStateSnapshot();
	}

	function applyGraphSnapshot(snapshot) {
		if (!Array.isArray(snapshot)) return;

		// Correctly re-split the flat snapshot array into nodes and edges.
		// Nodes are identified by having a 'type' and 'position', Edges by having a 'source'.
		const newNodes = snapshot.filter((el) => el.type && el.position);
		const newEdges = snapshot.filter((el) => el.source && el.target);

		nodes.value = deepClone(newNodes);
		edges.value = deepClone(newEdges);
	}

	function update_node_position(nodeId, position) {
		if (!nodeId || !position) return;
		const node = nodes.value.find((n) => n.id === nodeId);
		if (!node) return;
		node.position = {
			x: Math.round(position.x ?? node.position?.x ?? 0),
			y: Math.round(position.y ?? node.position?.y ?? 0),
		};
	}

	// ── Topological sort ──
	function getTopologicalSort(nodeList, edgeList) {
		nodeList = nodeList || nodes.value;
		edgeList = edgeList || edges.value;

		const adj = {};
		const processed = new Set();
		const result = [];
		nodeList.forEach((n) => (adj[n.id] = []));
		edgeList.forEach((e) => {
			if (adj[e.source]) adj[e.source].push(e.target);
		});

		const entryNode = nodeList.find(
			(n) => n.id === "start" || n.type === "start" || n.data?.action_type === "Entry Action"
		);
		if (entryNode && !processed.has(entryNode.id)) {
			processed.add(entryNode.id);
			result.push(entryNode);
		}

		let ptr = 0;
		while (ptr < result.length) {
			const current = result[ptr++];
			const children = adj[current.id] || [];
			children.forEach((childId) => {
				const childNode = nodeList.find((n) => n.id === childId);
				if (childNode && !processed.has(childId)) {
					processed.add(childId);
					result.push(childNode);
				}
			});
		}

		// Add any orphaned nodes not reached by BFS
		nodeList.forEach((n) => {
			if (!processed.has(n.id)) result.push(n);
		});

		return result;
	}

	// ── Available variables (upstream context) ──
	async function getAvailableVariables(upToNodeId = null, ruleDoc = null) {
		// Some callers pass action_id instead of node.id; normalize so upstream traversal works.
		let scopedNodeId = upToNodeId;
		if (
			scopedNodeId &&
			!nodes.value.some((n) => n.id === scopedNodeId) &&
			nodes.value.some((n) => n.data?.action_id === scopedNodeId)
		) {
			scopedNodeId = nodes.value.find((n) => n.data?.action_id === scopedNodeId)?.id || null;
		}

		const buildExecutionLinks = () => {
			const links = [];
			const seen = new Set();
			const addLink = (source, target, handle) => {
				if (!source || !target) return;
				const key = `${source}->${target}:${handle || "default"}`;
				if (seen.has(key)) return;
				seen.add(key);

				let h = handle || "default";
				const sourceNode = nodes.value.find((n) => n.id === source);
				// Treat legacy 'true' handle as 'default' for Loop nodes for scope propagation
				if (sourceNode?.data?.action_type === "Loop" && h === "true") {
					h = "default";
				}

				links.push({
					source,
					target,
					sourceHandle: h,
				});
			};

			(edges.value || []).forEach((edge) => {
				addLink(edge.source, edge.target, edge.sourceHandle);
			});

			(nodes.value || []).forEach((node) => {
				const data = node?.data || {};
				const trueHandle = data.action_type === "Condition" ? "true" : "default";
				addLink(node.id, data.next_step_if_true, trueHandle);
				addLink(node.id, data.next_step_if_false, "false");
			});

			return links;
		};

		const findUpstreamNodeIds = (targetId, links) => {
			if (!targetId) return null;
			const reverse = new Map();
			(links || []).forEach((link) => {
				if (!reverse.has(link.target)) reverse.set(link.target, []);
				reverse.get(link.target).push(link.source);
			});

			const stack = [targetId];
			const visited = new Set([targetId]);
			const upstream = new Set();
			while (stack.length) {
				const current = stack.pop();
				const sources = reverse.get(current) || [];
				sources.forEach((sourceId) => {
					if (visited.has(sourceId)) return;
					visited.add(sourceId);
					upstream.add(sourceId);
					stack.push(sourceId);
				});
			}

			return upstream;
		};

		const normalizeReturnVariable = (value) => {
			const raw = String(value || "").trim();
			if (!raw) return "";
			const noWrapper = raw.replace(/^\{\{\s*|\s*\}\}$/g, "");
			const noVarsPrefix = noWrapper.replace(/^vars\./, "");
			const noDocPrefix = noVarsPrefix.replace(/^doc\./, "");
			const normalized = noDocPrefix.replace(/\s+/g, "_").replace(/[^\w.]/g, "_");
			return normalized || noVarsPrefix || raw;
		};

		const startNode = nodes.value.find(
			(n) => n.id === "start" || n.type === "start" || n.data?.action_type === "Entry Action"
		);
		const doctype = ruleDoc?.document_type || startNode?.data?.document_type || null;

		// Initial pool: Standard doc fields (so they can be propagated into loops if iterating doc.items)
		const baseFields = doctype ? await flexirule.utils.get_doctype_fields(doctype, "doc") : [];
		const context_vars = [...baseFields];

		const seenContextValues = new Set(context_vars.map((v) => v.value));
		const executionLinks = buildExecutionLinks();
		const sortedNodes = getTopologicalSort(nodes.value, executionLinks);
		const upstreamNodeIds = findUpstreamNodeIds(scopedNodeId, executionLinks);
		const scopedNodes =
			scopedNodeId && upstreamNodeIds
				? sortedNodes.filter((n) => upstreamNodeIds.has(n.id))
				: sortedNodes;

		const isDownstreamOfHandle = (sourceId, targetId, handle, links) => {
			if (sourceId === targetId) return false;
			const q = [{ id: sourceId, first: true }];
			const visited = new Set();
			while (q.length) {
				const { id, first } = q.shift();
				if (id === targetId && !first) return true;
				if (visited.has(id)) continue;
				if (!first) visited.add(id);

				const children = links.filter(
					(l) => l.source === id && (first ? l.sourceHandle === handle : true)
				);
				children.forEach((c) => q.push({ id: c.target, first: false }));
			}
			return false;
		};

		// 1. Phase 1: Collect all base variables from upstream nodes
		for (const node of scopedNodes) {
			const data = node.data || {};

			// Add Loop root alias (base entry)
			if (data.action_type === "Loop") {
				const config = flexirule.utils.safe_json_parse(data.config, {});
				const itemVar = normalizeReturnVariable(
					data.return_variable || config.alias || "item"
				);
				const root = `vars.${itemVar}`;

				if (!seenContextValues.has(root)) {
					seenContextValues.add(root);
					context_vars.push({
						label: `vars.${itemVar} (${__("Loop Item")})`,
						value: root,
						fieldtype: "Data",
						is_variable: true,
						is_loop_scoped: true,
					});
				}
			}

			// Handle Return Variables and Schema
			const rawReturnVariable = String(data.return_variable || "").trim();
			const normalizedReturnVariable = normalizeReturnVariable(rawReturnVariable);

			if (normalizedReturnVariable) {
				const root = `vars.${normalizedReturnVariable}`;
				if (!seenContextValues.has(root)) {
					seenContextValues.add(root);
					context_vars.push({
						label: root,
						value: root,
						fieldtype: mapReturnTypeToFieldType(data.return_type),
						is_variable: true,
					});
				}

				// Propagate resolved output schema
				if (data.resolved_output_schema && data.return_type !== "Yes / No") {
					const schema = flexirule.utils.safe_json_parse(data.resolved_output_schema, []);
					if (Array.isArray(schema)) {
						schema.forEach((field) => {
							if (!field.fieldname) return;
							const schemaValue = `vars.${normalizedReturnVariable}.${field.fieldname}`;
							if (!seenContextValues.has(schemaValue)) {
								seenContextValues.add(schemaValue);
								context_vars.push({
									...field,
									label: `vars.${normalizedReturnVariable}.${field.fieldname} (${
										field.label || field.fieldname
									})`,
									value: schemaValue,
									is_variable: true,
								});
							}
						});
					}
				} else if (
					ACTION_TYPES_WITH_RETURN_SCHEMA.has(data.action_type) &&
					data.reference_doctype &&
					data.return_type !== "Yes / No"
				) {
					// Fallback to doctype fields if no explicit schema
					try {
						const dtFields = await flexirule.utils.get_doctype_fields(
							data.reference_doctype
						);
						dtFields.forEach((field) => {
							const schemaValue = `vars.${normalizedReturnVariable}.${field.value}`;
							if (!seenContextValues.has(schemaValue)) {
								seenContextValues.add(schemaValue);
								context_vars.push({
									...field,
									label: `vars.${normalizedReturnVariable}.${field.value} (${
										field.label || field.fieldname
									})`,
									value: schemaValue,
									is_variable: true,
								});
							}
						});
					} catch (e) {
						/* ignore */
					}
				}
			}
		}

		// 2. Phase 2: Perform Loop Schema Propagation
		// Iterate again to propagate fields into loop aliases, now that all base variables are collected.
		for (const node of scopedNodes) {
			const data = node.data || {};
			if (
				data.action_type === "Loop" &&
				scopedNodeId &&
				isDownstreamOfHandle(node.id, scopedNodeId, "default", executionLinks)
			) {
				const config = flexirule.utils.safe_json_parse(data.config, {});
				const itemVar = normalizeReturnVariable(
					data.return_variable || config.alias || "item"
				);
				const root = `vars.${itemVar}`;
				const iterator = config.iterator;

				if (iterator) {
					const rawPrefix = iterator.replace(/^\{\{\s*|\s*\}\}$/g, "").trim();
					const normalizedPrefix = normalizeReturnVariable(rawPrefix);

					const possiblePrefixes = [
						`vars.${normalizedPrefix}.`,
						`doc.${normalizedPrefix}.`,
						`${normalizedPrefix}.`,
					];

					// We only iterate over variables collected in Phase 1 (current state of context_vars)
					const baseVars = [...context_vars];
					baseVars.forEach((v) => {
						if (!v.value || v.is_loop_scoped) return; // Skip already scoped or invalid
						const valStr = String(v.value);
						const matchedPrefix = possiblePrefixes.find((p) => valStr.startsWith(p));

						if (matchedPrefix) {
							const suffix = valStr.slice(matchedPrefix.length);
							const subValue = `${root}.${suffix}`;
							if (!seenContextValues.has(subValue)) {
								seenContextValues.add(subValue);
								context_vars.push({
									...v,
									label: `${root}.${suffix} (${
										v.label_short || v.label || suffix
									})`,
									value: subValue,
									is_variable: true,
									is_loop_scoped: true,
								});
							}
						}
					});
				}

				// Add standard vars.loop metadata
				["index", "first", "last", "length"].forEach((key) => {
					const loopVar = `vars.loop.${key}`;
					if (!seenContextValues.has(loopVar)) {
						seenContextValues.add(loopVar);
						context_vars.push({
							label: `${loopVar} (${__("Loop Meta")})`,
							value: loopVar,
							fieldtype: key === "index" || key === "length" ? "Int" : "Check",
							is_variable: true,
						});
					}
				});
			}
		}

		return context_vars.reverse();
	}

	function mapReturnTypeToFieldType(returnType) {
		switch (returnType) {
			case "Yes / No":
				return "Check";
			case "List of Values":
			case "List of Records":
				return "Table";
			case "Single Record":
			case "Full Document":
				return "Data";
			default:
				return returnType || "Data";
		}
	}

	// ── Node operations ──
	function get_default_node_data(type, label = "") {
		const id = generateShortId();
		const actionType = normalizeActionType(flexirule.utils.to_title_case(type));
		const baseData = {
			action_id: id,
			action_type: actionType,
			action_label: label || `New ${actionType}`,
			is_enabled: 1,
			is_async: 0,
			skip_conditions: 1,
			mutation_mode: null,
		};

		// Type-specific defaults
		if (type === "condition") {
			baseData.action_type = "Condition";
			baseData.compiled_expression = "";
			baseData.config = { op: "and", conditions: [] };
			baseData.condition_json = null;
		} else if (type === "wait") {
			baseData.action_type = "Wait";
			baseData.config = { wait_type: "Duration", value: 1, unit: "Minutes" };
		} else if (type === "assignment") {
			baseData.action_type = "Assignment";
			baseData.config = [];
		} else if (type === "stop") {
			baseData.action_type = "Stop";
			baseData.operation = "Success";
		} else if (type === "raise-error" || type === "raise error") {
			baseData.action_type = "Raise Error";
			baseData.config = { error_type: "Validation Error" };
		} else if (type === "loop") {
			baseData.action_type = "Loop";
			baseData.config = { iterator: "" };
			baseData.return_variable = "item";
		} else if (type === "sub-rule") {
			baseData.action_type = "Sub-Rule";
		} else if (type === "query" || type === "query records") {
			baseData.action_type = "Query Records";
			baseData.operation = "Query List";
			baseData.return_variable = "query_result";
		}

		return baseData;
	}

	function delete_node(nodeId, isReadOnly = false) {
		if (isReadOnly) {
			frappe.msgprint(__("Cannot edit active rule. Please switch to Draft mode."));
			return false;
		}

		const node = nodes.value.find((el) => el.id === nodeId);
		if (
			nodeId === "start" ||
			nodeId === "root" ||
			node?.type === "start" ||
			node?.data?.action_type === "Entry Action"
		) {
			frappe.msgprint(__("Cannot delete start node"));
			return false;
		}

		const inEdges = edges.value.filter((e) => e.target === nodeId);
		const outEdges = edges.value.filter((e) => e.source === nodeId);
		const actionType = node?.data?.action_type;
		const isMultiOutput = ["Condition", "Loop", "Switch"].includes(actionType);

		// ── BFS helper: collect all node IDs reachable from `startId`,
		//   following only edges in `edgeList`, stopping at any ID in `stopSet`.
		function bfsFrom(startId, edgeList, stopSet = new Set()) {
			const visited = new Set();
			const q = [startId];
			while (q.length) {
				const id = q.shift();
				if (visited.has(id) || stopSet.has(id)) continue;
				visited.add(id);
				edgeList.forEach((e) => {
					if (e.source === id && !visited.has(e.target)) q.push(e.target);
				});
			}
			return visited;
		}

		if (isMultiOutput && outEdges.length > 1) {
			// Determine which output is the "primary continuation" (kept) vs "secondary" (cascade-delete).
			// Loop  → primary = "After Last" (sourceHandle === "false")
			// Condition / Switch → primary = YES / True (sourceHandle !== "false")
			const isPrimaryFalse = actionType === "Loop";
			const primaryEdge = outEdges.find((e) =>
				isPrimaryFalse ? e.sourceHandle === "false" : e.sourceHandle !== "false"
			);
			const secondaryEdges = outEdges.filter((e) => e !== primaryEdge);

			// Reconnect parents to the primary target
			const primaryTargetId = primaryEdge?.target ?? null;
			inEdges.forEach((inEdge) => {
				inEdge.target = primaryTargetId;
				const srcNode = nodes.value.find((n) => n.id === inEdge.source);
				if (srcNode?.data) {
					if (inEdge.sourceHandle === "false") {
						srcNode.data.next_step_if_false = primaryTargetId;
					} else {
						srcNode.data.next_step_if_true = primaryTargetId;
					}
				}
			});

			// Cascade-delete nodes ONLY reachable from secondary outputs
			// (i.e. nodes that would be orphaned and unreachable from the rest of the graph)
			const edgesWithoutRemoved = edges.value.filter(
				(e) => e.source !== nodeId && e.target !== nodeId
			);
			// Build set of all IDs still reachable from the main graph root
			const rootId =
				nodes.value.find(
					(n) => n.type === "start" || n.data?.action_type === "Entry Action"
				)?.id || "root";
			const mainReachable = bfsFrom(rootId, [
				...edgesWithoutRemoved,
				// include the reconnected in-edges so the primary target is reachable
				...inEdges.map((e) => ({ ...e, target: primaryTargetId })),
			]);

			const toDelete = new Set([nodeId]);
			secondaryEdges.forEach((e) => {
				if (!e.target || mainReachable.has(e.target)) return;
				bfsFrom(e.target, edgesWithoutRemoved, mainReachable).forEach((id) =>
					toDelete.add(id)
				);
			});

			nodes.value = nodes.value.filter((n) => !toDelete.has(n.id));
			edges.value = edges.value.filter(
				(e) => !toDelete.has(e.source) && !toDelete.has(e.target)
			);

			// Fix reconnected in-edge targets in the edge array
			edges.value = edges.value.map((e) => {
				if (e.target === nodeId) return { ...e, target: primaryTargetId };
				return e;
			});

			return true;
		}

		// ── Simple single-output reconnection ────────────────────────────────
		if (outEdges.length === 1) {
			const targetId = outEdges[0].target;
			inEdges.forEach((inEdge) => {
				inEdge.target = targetId;
				const sourceNode = nodes.value.find((n) => n.id === inEdge.source);
				if (sourceNode && sourceNode.data) {
					if (inEdge.sourceHandle === "false") {
						sourceNode.data.next_step_if_false = targetId;
					} else {
						sourceNode.data.next_step_if_true = targetId;
					}
				}
			});
		} else {
			// Zero or unresolvable outputs: just clear parent references
			inEdges.forEach((inEdge) => {
				const sourceNode = nodes.value.find((n) => n.id === inEdge.source);
				if (sourceNode && sourceNode.data) {
					if (inEdge.sourceHandle === "false") {
						sourceNode.data.next_step_if_false = null;
					} else {
						sourceNode.data.next_step_if_true = null;
					}
				}
			});
		}

		nodes.value = nodes.value.filter((el) => el.id !== nodeId);
		const outEdgeIds = new Set(outEdges.map((e) => e.id));
		edges.value = edges.value.filter(
			(el) => !outEdgeIds.has(el.id) && el.source !== nodeId && el.target !== nodeId
		);

		return true;
	}

	function toggle_node_enabled(nodeId) {
		const node = nodes.value.find((n) => n.id === nodeId);
		if (!node || !node.data) return;

		// Default to enabled (1) if undefined
		if (node.data.is_enabled === 0) {
			node.data.is_enabled = 1;
		} else {
			node.data.is_enabled = 0;
		}

		// Force reactivity update if needed
		nodes.value = [...nodes.value];
	}

	function delete_edge(edgeId, isReadOnly = false) {
		if (isReadOnly) return false;
		const edge = edges.value.find((el) => el.id === edgeId);
		if (!edge) return false;

		// Clear the next_step reference in the source node's data
		const sourceNode = nodes.value.find((el) => el.id === edge.source);
		if (sourceNode && sourceNode.data) {
			const handle = edge.sourceHandle || "default";
			if (handle === "false") {
				if (sourceNode.data.next_step_if_false === edge.target) {
					sourceNode.data.next_step_if_false = null;
				}
			} else if (handle === "true" || handle === "default") {
				if (sourceNode.data.next_step_if_true === edge.target) {
					sourceNode.data.next_step_if_true = null;
				}
			}
		}

		edges.value = edges.value.filter((el) => el.id !== edgeId);
		return true;
	}

	function insert_node_on_edge(edgeId, nodeType = "selector", options = {}) {
		const edge = edges.value.find((e) => e.id === edgeId);
		if (!edge) return;

		const sourceId = edge.source;
		const targetId = edge.target;
		const sourceHandle = edge.sourceHandle || "default";

		// 1. Create new node
		const newNodeId = generateShortId();
		const nodeData = get_default_node_data(nodeType, options.label);

		// Apply options (operation, process_name)
		if (options.operation) nodeData.operation = options.operation;
		if (options.process_name) nodeData.process_name = options.process_name;

		const actionType = nodeData.action_type;

		// ── LOOP: "For Each" branch gets a selector in the loop body.
		//         "After Last" continues to the existing downstream target.
		if (actionType === "Loop") {
			// Scaffold an empty selector node as the loop body entry
			const bodyNodeId = generateShortId();
			const bodyData = get_default_node_data("selector", __("Loop Body"));
			bodyData.action_id = bodyNodeId;

			const bodyNode = {
				id: bodyNodeId,
				type: "selector",
				position: { x: 0, y: 0 },
				label: __("Loop Body"),
				data: { ...bodyData, next_step_if_true: newNodeId },
			};

			// Loop: For Each (default) → body entry; After Last (false) → existing target
			nodeData.next_step_if_true = bodyNodeId;
			nodeData.next_step_if_false = targetId;

			const newNode = {
				id: newNodeId,
				type: mapActionTypeToNodeType(actionType),
				position: { x: 0, y: 0 },
				label: nodeData.action_label,
				data: { ...nodeData, action_id: newNodeId },
			};

			delete_edge(edgeId);
			const sourceNode = nodes.value.find((n) => n.id === sourceId);
			if (sourceNode?.data) {
				if (sourceHandle === "false") {
					sourceNode.data.next_step_if_false = newNodeId;
				} else {
					sourceNode.data.next_step_if_true = newNodeId;
				}
			}

			nodes.value = [...nodes.value, newNode, bodyNode];

			edges.value = [
				...edges.value,
				// Source → Loop
				{
					id: `e-${sourceId}-${newNodeId}-${sourceHandle}`,
					source: sourceId,
					target: newNodeId,
					sourceHandle,
					type: "add",
				},
				// Loop → For Each → Body entry
				{
					id: `e-${newNodeId}-${bodyNodeId}-default`,
					source: newNodeId,
					target: bodyNodeId,
					sourceHandle: "default",
					type: "add",
					data: { loopBody: true },
				},
				// Loop body return edge
				{
					id: `e-${bodyNodeId}-${newNodeId}-return`,
					source: bodyNodeId,
					target: newNodeId,
					targetHandle: "return",
					type: "add",
					data: { isReturn: true },
				},
				// Loop → After Last → Existing target (main flow)
				{
					id: `e-${newNodeId}-${targetId}-false`,
					source: newNodeId,
					target: targetId,
					sourceHandle: "false",
					type: "add",
					data: { afterLast: true },
				},
			];

			return newNodeId;
		}

		// ── CONDITION / SWITCH: True/YES → existing target,
		//                        False/NO  → auto-scaffolded Stop. ──
		if (actionType === "Condition" || actionType === "Switch") {
			nodeData.next_step_if_true = targetId;

			const stopNodeId = generateShortId();
			const stopData = get_default_node_data("stop");
			stopData.operation = "Success";
			stopData.action_id = stopNodeId;

			const stopNode = {
				id: stopNodeId,
				type: "stop",
				position: { x: 0, y: 0 },
				label: __("End"),
				data: { ...stopData },
			};

			nodeData.next_step_if_false = stopNodeId;

			const newNode = {
				id: newNodeId,
				type: mapActionTypeToNodeType(actionType),
				position: { x: 0, y: 0 },
				label: nodeData.action_label,
				data: { ...nodeData, action_id: newNodeId },
			};

			delete_edge(edgeId);
			const sourceNode = nodes.value.find((n) => n.id === sourceId);
			if (sourceNode?.data) {
				if (sourceHandle === "false") {
					sourceNode.data.next_step_if_false = newNodeId;
				} else {
					sourceNode.data.next_step_if_true = newNodeId;
				}
			}

			nodes.value = [...nodes.value, newNode, stopNode];
			edges.value = [
				...edges.value,
				{
					id: `e-${sourceId}-${newNodeId}-${sourceHandle}`,
					source: sourceId,
					target: newNodeId,
					sourceHandle,
					type: "add",
				},
				// YES / True path → existing target (sourceHandle MUST be "true")
				{
					id: `e-${newNodeId}-${targetId}-true`,
					source: newNodeId,
					target: targetId,
					sourceHandle: "true",
					type: "add",
				},
				// NO / False path → new Stop
				{
					id: `e-${newNodeId}-${stopNodeId}-false`,
					source: newNodeId,
					target: stopNodeId,
					sourceHandle: "false",
					type: "add",
				},
			];

			return newNodeId;
		}

		// ── Simple single-output node (default behaviour) ──
		const isTerminal = isTerminalAction(nodeData.action_type);
		if (!isTerminal) {
			nodeData.next_step_if_true = targetId;
		}

		const newNode = {
			id: newNodeId,
			type: mapActionTypeToNodeType(nodeData.action_type),
			position: { x: 0, y: 0 },
			label: nodeData.action_label,
			data: {
				...nodeData,
				action_id: newNodeId,
			},
		};

		// 2. Remove old edge
		delete_edge(edgeId);

		// 3. Update source node pointer to new node
		const sourceNode = nodes.value.find((n) => n.id === sourceId);
		if (sourceNode && sourceNode.data) {
			if (sourceHandle === "false") {
				sourceNode.data.next_step_if_false = newNodeId;
			} else {
				sourceNode.data.next_step_if_true = newNodeId;
			}
		}

		// 4. Add new node
		nodes.value = [...nodes.value, newNode];

		// 5. Create new edges
		const edge1Id = `e-${sourceId}-${newNodeId}-${sourceHandle}`;
		const newEdges = [
			{
				id: edge1Id,
				source: sourceId,
				target: newNodeId,
				sourceHandle: sourceHandle,
				type: "add",
			},
		];

		// ONLY create outgoing edge if NOT terminal
		if (!isTerminalAction(nodeData.action_type)) {
			const edge2Id = `e-${newNodeId}-${targetId}-default`;
			newEdges.push({
				id: edge2Id,
				source: newNodeId,
				target: targetId,
				sourceHandle: "default",
				targetHandle: edge.targetHandle, // Propagate return handle if applicable
				type: "add",
				data: { ...(edge.data || {}) }, // Propagate flags like loopBody or isReturn
			});
		}

		edges.value = [...edges.value, ...newEdges];

		// 6. If terminal, remove orphaned target node (as requested)
		if (isTerminal) {
			const otherParents = edges.value.filter((e) => e.target === targetId);
			if (otherParents.length === 0) {
				// No other parents remaining, delete the target subtree
				delete_node(targetId);
			}
		}

		return newNodeId;
	}

	function paste_on_edge(edgeId, pastedNodes, pastedEdges) {
		const edge = edges.value.find((e) => e.id === edgeId);
		if (!edge || !pastedNodes?.length) return;

		const sourceId = edge.source;
		const targetId = edge.target;
		const sourceHandle = edge.sourceHandle || "default";

		// 1. Paste nodes and get new ones
		const newNodes = pasteNodes(pastedNodes, pastedEdges, { x: 0, y: 0 });
		if (!newNodes.length) return;

		const newNodeIds = new Set(newNodes.map((n) => n.id));

		// 2. Identify entry and exit points in the pasted block
		// Entry: first node that doesn't have an incoming FORWARD edge from another pasted node
		const entryNode = newNodes.find((n) => {
			return !edges.value.some(
				(e) => e.target === n.id && newNodeIds.has(e.source) && !e.data?.isReturn
			);
		});

		// Exit: first node that has a "null" next step (meaning it originally pointed outside the selection)
		const exitNode = newNodes.find((n) => {
			if (isTerminalAction(n.data?.action_type)) return false;
			// For multi-output nodes like Loop/Condition, we check if ANY output is now null
			return n.data?.next_step_if_true === null || n.data?.next_step_if_false === null;
		});

		if (!entryNode) {
			// Fallback: if we can't find clear entry, return the first node but connectivity will be partial
			return newNodes[0].id;
		}

		// 3. Remove old edge
		delete_edge(edgeId);

		// 4. Connect source to entry node
		const sourceNode = nodes.value.find((n) => n.id === sourceId);
		if (sourceNode && sourceNode.data) {
			if (sourceHandle === "false") {
				sourceNode.data.next_step_if_false = entryNode.id;
			} else {
				sourceNode.data.next_step_if_true = entryNode.id;
			}
		}

		const entryEdge = {
			id: `e-${sourceId}-${entryNode.id}-${sourceHandle}`,
			source: sourceId,
			target: entryNode.id,
			sourceHandle: sourceHandle,
			type: "add",
		};

		// 5. Connect exit node to target if NOT terminal
		const newEdgesToAdd = [entryEdge];
		if (exitNode && !isTerminalAction(exitNode.data?.action_type)) {
			// Determine which handle to use on the exit node.
			// Prefer the 'false' handle if it's the one that was nulled (e.g. Loop After Last)
			const useFalseHandle = exitNode.data.next_step_if_false === null;
			const exitHandle = useFalseHandle ? "false" : "default";

			if (exitNode.data) {
				if (useFalseHandle) {
					exitNode.data.next_step_if_false = targetId;
				} else {
					exitNode.data.next_step_if_true = targetId;
				}
			}

			newEdgesToAdd.push({
				id: `e-${exitNode.id}-${targetId}-${exitHandle}`,
				source: exitNode.id,
				target: targetId,
				sourceHandle: exitHandle,
				type: "add",
				data: useFalseHandle ? { afterLast: exitNode.data?.action_type === "Loop" } : {},
			});
		}

		edges.value = [...edges.value, ...newEdgesToAdd];

		return entryNode.id;
	}

	function touch_node(nodeId) {
		if (!nodeId) return;
		const idx = nodes.value.findIndex((n) => n.id === nodeId);
		if (idx === -1) return;

		const current = nodes.value[idx];
		// Replace to trigger Vue reactivity
		nodes.value[idx] = {
			...current,
			data: { ...(current.data || {}) },
		};
	}

	// ── Data cleaning ──
	function clean_graph_data() {
		return [...nodes.value, ...edges.value].map((el) => {
			const { selected, dragging, resizing, sourceNode, targetNode, ...obj } = el;
			if (obj.data?.action_type) {
				obj.data.action_type = normalizeActionType(obj.data.action_type);
			}
			return obj;
		});
	}

	function toDocExpression(path) {
		if (!path || typeof path !== "string") return "";
		if (path.startsWith("doc.") || path.startsWith("vars.") || path.startsWith("frappe.")) {
			return path;
		}
		return `doc.${path}`;
	}

	function legacySourceToExpression(source) {
		if (!source || typeof source !== "object") return null;
		const kind = source.kind || "date_formula";

		if (kind === "date_formula") {
			const baseType = source.base_type || "today";
			const baseExpr =
				baseType === "doc_field"
					? toDocExpression(source.base_field || "")
					: "frappe.utils.nowdate()";
			const offset = Number(source.offset_value || 0);
			const unit = source.offset_unit || "days";
			if (!offset) return baseExpr;
			if (unit === "days") {
				return `frappe.utils.add_days(${baseExpr}, ${offset})`;
			}
			return `frappe.utils.add_to_date(${baseExpr}, ${unit}=${offset})`;
		}

		if (kind === "math_formula") {
			const a = source.field_a ? `frappe.utils.flt(${toDocExpression(source.field_a)})` : "0";
			const b =
				source.field_b_type === "constant"
					? String(source.constant_b ?? 0)
					: source.field_b
					? `frappe.utils.flt(${toDocExpression(source.field_b)})`
					: "0";
			const op = source.math_op || "+";
			const precision = Number.isFinite(Number(source.precision))
				? Number(source.precision)
				: 2;
			return `frappe.utils.flt(${a} ${op} ${b}, ${precision})`;
		}

		if (kind === "date_diff") {
			const start =
				source.diff_start_type === "doc_field"
					? toDocExpression(source.diff_start_field || "")
					: "frappe.utils.nowdate()";
			const end =
				source.diff_end_type === "doc_field"
					? toDocExpression(source.diff_end_field || "")
					: "frappe.utils.nowdate()";
			const unit = source.diff_unit || "days";
			if (unit === "months") return `frappe.utils.month_diff(${end}, ${start})`;
			if (unit === "years") return `int(frappe.utils.month_diff(${end}, ${start}) / 12)`;
			return `frappe.utils.date_diff(${end}, ${start})`;
		}

		return null;
	}

	function getProcessSchemaPropertyNames(processName, operation) {
		if (!processName || !operation) return [];
		const opDef = getProcessOperationDefinition(processName, operation);
		const schema = opDef?.contract_v2?.config_schema;
		const properties = schema?.properties;
		if (!properties || typeof properties !== "object") return [];
		return Object.keys(properties);
	}

	function normalizeProcessConfigLegacyShape(config, processName, operation) {
		if (!config || typeof config !== "object" || Array.isArray(config)) return config;
		const normalized = { ...config };

		if (!normalized.source_value && normalized.source) {
			if (typeof normalized.source === "string") {
				normalized.source_value = normalized.source;
			} else {
				const expression = legacySourceToExpression(normalized.source);
				if (expression) normalized.source_value = expression;
			}
		}

		if (
			normalized.source_field &&
			typeof normalized.source_field === "object" &&
			normalized.source_field.value
		) {
			normalized.source_field = normalized.source_field.value;
		}

		if (
			normalized.target_field &&
			typeof normalized.target_field === "object" &&
			normalized.target_field.value
		) {
			normalized.target_field = normalized.target_field.value;
		}

		const allowedKeys = getProcessSchemaPropertyNames(processName, operation);
		if (allowedKeys.length > 0) {
			const pruned = {};
			allowedKeys.forEach((key) => {
				if (normalized[key] !== undefined) {
					pruned[key] = normalized[key];
				}
			});
			return pruned;
		}

		return normalized;
	}

	function clean_action_config(config, opts = {}) {
		if (!config || typeof config !== "object") return config;
		const clean = Array.isArray(config) ? [...config] : { ...config };
		const actionType = normalizeActionType(opts?.actionType || "");
		const processName = opts?.processName || null;
		const operation = opts?.operation || null;

		if (actionType === "Process") {
			const normalizedProcessConfig = normalizeProcessConfigLegacyShape(
				clean,
				processName,
				operation
			);
			return normalizedProcessConfig;
		}

		// Clean filters
		if (Array.isArray(clean.filters)) {
			clean.filters = clean.filters.filter((f) => {
				// New tuple format: [doctype, field, op, payload]
				if (Array.isArray(f)) {
					return typeof f[1] === "string" && f[1].trim() !== "";
				}
				// Legacy object format: { doctype, field, operator, value, ... }
				return !!(f?.field || f?.fieldname);
			});
		}

		// Clean field lists
		if (Array.isArray(clean.fields)) {
			clean.fields = clean.fields.filter((f) => f && f.trim?.() !== "");
		}

		// Clean field_mappings
		if (Array.isArray(clean.field_mappings)) {
			clean.field_mappings = clean.field_mappings.filter((m) => m.source && m.target);
		}

		// Clean static_values
		if (clean.static_values && typeof clean.static_values === "object") {
			const cleaned_static = {};
			Object.entries(clean.static_values).forEach(([k, v]) => {
				if (k && k.trim() !== "") cleaned_static[k] = v;
			});
			clean.static_values = cleaned_static;
		}

		if (
			clean.input_mapping &&
			typeof clean.input_mapping === "object" &&
			!Array.isArray(clean.input_mapping) &&
			!Object.keys(clean.input_mapping).length
		) {
			delete clean.input_mapping;
		}

		if (
			clean.output_mapping &&
			typeof clean.output_mapping === "object" &&
			!Array.isArray(clean.output_mapping) &&
			!Object.keys(clean.output_mapping).length
		) {
			delete clean.output_mapping;
		}

		if (
			typeof clean.permission_audit_reason === "string" &&
			!clean.permission_audit_reason.trim()
		) {
			delete clean.permission_audit_reason;
		}

		return clean;
	}

	// ── Normalization ──
	function normalize_action_data(actionType, data = {}) {
		if (!actionType || !data) return data;

		// Bridging machine node types to canonical contract keys
		actionType = normalizeActionType(actionType);

		const normalized = { ...data, action_type: actionType };
		const contract = getContract(actionType);
		const operationOptions = getOperationOptions(actionType, {
			processName: normalized.process_name,
		}).map((opt) => opt.value);

		if (
			normalized.operation &&
			operationOptions.length &&
			!operationOptions.includes(normalized.operation)
		) {
			normalized.operation = null;
		}

		const policy = getEffectiveActionPolicy(actionType, {
			operation: normalized.operation,
			processName: normalized.process_name,
		});
		const allowedMutations = policy.allowed_mutations || contract.allowed_mutations || [];
		const allowedReturnTypes =
			policy.allowed_return_types || contract.allowed_return_types || [];

		if (
			normalized.mutation_mode &&
			(!allowedMutations.length || !allowedMutations.includes(normalized.mutation_mode))
		) {
			normalized.mutation_mode = null;
		}

		if (!ACTION_TYPES_WITH_REFERENCE_CONTEXT.has(actionType)) {
			normalized.input_source = null;
			normalized.reference_doctype = null;
			normalized.reference_docname = null;
		}

		if (!ACTION_TYPES_WITH_RETURN_SCHEMA.has(actionType)) {
			normalized.return_type = null;
			normalized.resolved_output_schema = null;
		} else {
			if (
				normalized.return_type &&
				allowedReturnTypes.length &&
				!allowedReturnTypes.includes(normalized.return_type)
			) {
				normalized.return_type = null;
			}
			if (!normalized.return_type && policy.default_return_type) {
				normalized.return_type = policy.default_return_type;
			}
		}

		if (actionType !== "Process") normalized.process_name = null;
		if (actionType !== "Sub-Rule") normalized.rule = null;
		if (actionType !== "Condition") {
			normalized.compiled_expression = null;
			normalized.condition_json = null;
			normalized.next_step_if_false = null;
		} else {
			normalized.condition_json = null;
		}
		if (contract.terminal) {
			normalized.next_step_if_true = null;
			normalized.next_step_if_false = null;
		}
		if (actionType === "Stop" && normalized.operation !== "Error") {
			normalized.value_template = null;
		}

		return normalized;
	}

	function normalize_graph_nodes() {
		nodes.value = nodes.value.map((node) => {
			if (!node.data?.action_type) return node;

			// 1. Deep sync conditions to config before normalization
			if (node.data.action_type === "Condition") {
				const payload = getConditionPayload({
					config: node.data.config,
					condition_json: node.data.condition_json,
				});
				if (payload) {
					node.data.config = payload;
					node.data.condition_json = null;
				}
				if (!node.data.config || typeof node.data.config !== "object") {
					node.data.config = { op: "and", conditions: [] };
				}
			}

			// 2. Structural normalization for Assignments
			if (node.data.action_type === "Assignment") {
				if (!node.data.config || !Array.isArray(node.data.config)) {
					node.data.config = [];
				}
			}

			if (node.type === "start") return node;

			return {
				...node,
				data: normalize_action_data(node.data.action_type, node.data),
			};
		});
	}

	// ── Sync: Rule Actions → Graph Nodes/Edges ──

	function getSubRuleName(configStr) {
		try {
			const parsed = typeof configStr === "string" ? JSON.parse(configStr) : configStr;
			return parsed?.sub_rule_name || parsed?.rule || null;
		} catch {
			return null;
		}
	}

	/**
	 * Build graph nodes and edges from a Rule document's actions array.
	 * This is the central sync function — mirrors Frappe's get_workflow_elements().
	 *
	 * @param {Object} ruleDoc - The rule document
	 * @param {Array} customActions — optional override for actions list
	 */
	function sync_actions_to_graph(ruleDoc, customActions = null) {
		const actionNodes = [];
		const actionEdges = [];

		const actionsList = customActions || ruleDoc.actions || [];
		const visualData = flexirule.utils.safe_json_parse(ruleDoc.visual_data, {});
		const visualNodes = new Map((visualData.nodes || []).map((n) => [n.id, n]));

		// Ensure we have a root/entry action node
		const rootAction = actionsList.find(
			(a) => a.action_type === "Entry Action" || a.action_id === "root"
		);

		if (!rootAction) {
			actionNodes.push({
				id: "start",
				type: "start",
				position: { x: 50, y: 250 },
				label: "Start",
				data: {
					action_id: "start",
					action_type: "Entry Action",
					trigger_type: ruleDoc.trigger_type,
					document_type: ruleDoc.document_type,
					trigger_event: ruleDoc.trigger_event,
					compiled_expression: ruleDoc.compiled_expression,
					trigger_condition: ruleDoc.trigger_condition,
					is_enabled: 1,
				},
			});
		}

		for (const [index, action] of actionsList.entries()) {
			const nodeId = action.action_id || `act_${index}`;
			const originalActionType = (action.action_type || "Process").trim();
			const actionTypeRaw = normalizeActionType(originalActionType);
			let type = mapActionTypeToNodeType(actionTypeRaw);

			if (originalActionType === "Raise Error" && action.operation === "Error") {
				let parsedConfig = {};
				if (action.config && typeof action.config === "string") {
					try {
						parsedConfig = JSON.parse(action.config) || {};
					} catch (e) {
						parsedConfig = {};
					}
				} else if (action.config && typeof action.config === "object") {
					parsedConfig = { ...action.config };
				}
				if (!parsedConfig.error_type) {
					parsedConfig.error_type = "Validation Error";
				}
				action.config = parsedConfig;
				action.operation = null;
			}

			const isRoot =
				actionTypeRaw === "Entry Action" || nodeId === "start" || nodeId === "root";

			if (isRoot) type = "start";

			const nodeLabel = isRoot ? "Start" : action.action_label || `Action ${index + 1}`;
			const safeParse = (val, defaultVal = null) => {
				if (val && typeof val === "object") return val;
				return flexirule.utils.safe_json_parse(val, defaultVal);
			};

			const rawConfigData = safeParse(action.config, {}) || {};
			const configData =
				actionTypeRaw === "Process"
					? clean_action_config(rawConfigData, {
							actionType: "Process",
							processName: action.process_name,
							operation: action.operation,
					  }) || {}
					: rawConfigData;
			const conditionPayload =
				actionTypeRaw === "Condition"
					? getConditionPayload({
							config: configData,
							condition_json: action.condition_json,
					  })
					: null;
			const effectiveConfig =
				actionTypeRaw === "Condition"
					? conditionPayload || configData || { op: "and", conditions: [] }
					: configData;

			const nodeData = {
				action_id: nodeId,
				action_type: actionTypeRaw,
				action_label: action.action_label,
				process_name: action.process_name,
				operation: action.operation,
				config: effectiveConfig,
				target_field: action.target_field,
				value_template: action.value_template,
				compiled_expression: action.compiled_expression,
				condition_json: null,
				is_enabled: action.is_enabled,
				on_error: action.on_error,
				timeout: action.timeout,
				priority: action.priority,
				retry_count: action.retry_count,
				return_variable: action.return_variable,
				is_async: action.is_async,
				name: action.name,
				rule:
					action.rule ||
					(actionTypeRaw === "Sub-Rule" ? getSubRuleName(effectiveConfig) : null),
				skip_conditions: action.skip_conditions !== undefined ? action.skip_conditions : 1,
				skip_permissions: action.skip_permissions || 0,
				next_step_if_true: action.next_step_if_true,
				next_step_if_false: action.next_step_if_false,
				input_source: action.input_source,
				reference_doctype: action.reference_doctype,
				reference_docname: action.reference_docname,
				mutation_mode: action.mutation_mode,
				return_type: action.return_type,
				resolved_output_schema: safeParse(action.resolved_output_schema),
				input_mapping: effectiveConfig.input_mapping || null,
				output_mapping: effectiveConfig.output_mapping || null,
			};

			if (isRoot) {
				nodeData.trigger_type = ruleDoc.trigger_type;
				nodeData.document_type = ruleDoc.document_type;
				nodeData.trigger_event = ruleDoc.trigger_event;
				nodeData.trigger_condition = ruleDoc.trigger_condition;
				nodeData.compiled_expression = ruleDoc.compiled_expression;
				nodeData.priority = ruleDoc.priority;
				nodeData.execution_mode = ruleDoc.execution_mode;
				nodeData.max_execution_time = ruleDoc.max_execution_time;
				nodeData.debug_mode = ruleDoc.debug_mode;
				nodeData.skip_for_roles = (ruleDoc.skip_for_roles || [])
					.map((row) => row.role)
					.filter(Boolean);
				nodeData.permissions = (ruleDoc.permissions || []).map((row) => ({
					role: row.role,
					can_execute: row.can_execute || 0,
				}));
				nodeData.description = ruleDoc.description;
				nodeData.exposed_as_subrule = ruleDoc.exposed_as_subrule ?? 0;
				nodeData.version = ruleDoc.version;
				nodeData.status = ruleDoc.status;
				nodeData.is_active = ruleDoc.is_active;
			}

			actionNodes.push({
				id: nodeId,
				type: type,
				position: {
					x: isRoot ? 50 : 300,
					y: isRoot ? 250 : 150 + index * 200,
				},
				label: nodeLabel,
				data: nodeData,
				className: "",
				style: {},
			});
		}

		// Build edges from next_step references
		const sourceActions = customActions || actionsList;
		sourceActions.forEach((action, index) => {
			const nodeId = action.action_id || `act_${index}`;
			if (action.next_step_if_true) {
				const isLoopBody = action.action_type === "Loop";
				const isReturnToLoop =
					actionsList.find((a) => a.action_id === action.next_step_if_true)
						?.action_type === "Loop" && action.action_type !== "Entry Action";
				actionEdges.push({
					id: `e-${nodeId}-${action.next_step_if_true}-true`,
					source: nodeId,
					target: action.next_step_if_true,
					sourceHandle: action.action_type === "Condition" ? "true" : "default",
					targetHandle: isReturnToLoop ? "return" : null,
					type: "add",
					animated: action.action_type === "Entry Action",
					data: {
						loopBody: isLoopBody,
						isReturn: isReturnToLoop,
					},
				});
			}
			if (action.next_step_if_false) {
				actionEdges.push({
					id: `e-${nodeId}-${action.next_step_if_false}-false`,
					source: nodeId,
					target: action.next_step_if_false,
					sourceHandle: "false",
					type: "add",
					data: { afterLast: action.action_type === "Loop" },
				});
			}
		});

		nodes.value = [...actionNodes];
		edges.value = [...actionEdges];
	}

	/**
	 * Merge saved visual positions onto current graph nodes.
	 * Only merges positions + meta — never overwrites data.
	 *
	 * @param {Array} visual_data - The parsed visual_data JSON
	 */
	function merge_visual_layout(visual_data) {
		const visualNodes = new Map(
			(visual_data || []).filter((el) => el.position).map((node) => [node.id, node])
		);
		const visualEdges = new Map(
			(visual_data || [])
				.filter((el) => el.source)
				.map((edge) => [
					`${edge.source}:${edge.target}:${edge.sourceHandle || "default"}`,
					edge,
				])
		);

		// 1. Merge node positions
		const seenNodeIds = new Set();
		const mergedNodes = nodes.value.map((node) => {
			seenNodeIds.add(node.id);
			const visualNode = visualNodes.get(node.id);
			if (!visualNode) return node;

			const {
				position,
				type: _visualType,
				label: _visualLabel,
				id: _visualId,
				data: _visualData,
				...visualNodeMeta
			} = visualNode;

			const direction = visualNode.direction || visualNode.layout_direction || null;
			return {
				...node,
				...visualNodeMeta,
				position: position || node.position,
				direction: direction || node.direction,
				data: { ...(node.data || {}) },
				type: node.type,
				label: node.label,
			};
		});

		// 2. Add orphaned visual nodes not in actions
		visualNodes.forEach((vNode, id) => {
			if (!seenNodeIds.has(id)) {
				mergedNodes.push({
					...vNode,
					data: { ...(vNode.data || {}) },
				});
				seenNodeIds.add(id);
			}
		});

		nodes.value = [...mergedNodes];

		// 3. Merge edge metadata
		const seenEdgeKeys = new Set();
		const mergedEdges = edges.value.map((edge) => {
			const key = `${edge.source}:${edge.target}:${edge.sourceHandle || "default"}`;
			seenEdgeKeys.add(key);
			const visualEdge = visualEdges.get(key);
			if (!visualEdge) return edge;

			const {
				id: _vId,
				source: _vSource,
				target: _vTarget,
				sourceHandle: _vSourceHandle,
				data: _vData,
				...visualEdgeMeta
			} = visualEdge;

			return { ...edge, ...visualEdgeMeta, type: "add" };
		});

		// Add orphaned edges with valid endpoints
		visualEdges.forEach((vEdge, key) => {
			if (!seenEdgeKeys.has(key)) {
				if (seenNodeIds.has(vEdge.source) && seenNodeIds.has(vEdge.target)) {
					mergedEdges.push({ ...vEdge, type: "add" });
					seenEdgeKeys.add(key);
				}
			}
		});

		edges.value = [...mergedEdges];
	}

	function get_visual_data_payload(layoutDirection = null) {
		const nodePayload = nodes.value.map((node) => ({
			id: node.id,
			position: {
				x: Math.round(node.position?.x || 0),
				y: Math.round(node.position?.y || 0),
			},
			direction: layoutDirection || node.direction || null,
		}));

		const edgePayload = edges.value.map((edge) => ({
			id: edge.id,
			source: edge.source,
			target: edge.target,
			sourceHandle: edge.sourceHandle || "default",
			targetHandle: edge.targetHandle || null,
		}));

		return [...nodePayload, ...edgePayload];
	}

	/**
	 * Initialize a default Trigger → End graph when a Rule has no actions.
	 *
	 * @param {Object} ruleDoc - Rule document
	 */
	function initialize_default_graph(ruleDoc) {
		nodes.value = [
			{
				id: "root",
				type: "start",
				position: { x: 250, y: 50 },
				label: "Start",
				data: {
					action_id: "root",
					action_type: "Entry Action",
					trigger_type: ruleDoc.trigger_type,
					document_type: ruleDoc.document_type,
					trigger_event: ruleDoc.trigger_event,
					trigger_condition: ruleDoc.trigger_condition,
					is_enabled: 1,
				},
			},
			{
				id: "node_end",
				type: "stop",
				position: { x: 250, y: 200 },
				label: "End",
				data: {
					action_id: "node_end",
					action_type: "Stop",
					is_enabled: 1,
					operation: "Success",
				},
			},
		];
		edges.value = [
			{
				id: "edge_root_node_end",
				source: "root",
				target: "node_end",
				sourceHandle: "true",
				type: "add",
				animated: true,
			},
		];
	}

	/**
	 * Paste nodes and edges from clipboard into the current graph.
	 * Remaps IDs to prevent collisions and preserves internal connections.
	 */
	function pasteNodes(pastedNodes, pastedEdges, position = { x: 0, y: 0 }) {
		if (!pastedNodes || !pastedNodes.length) return [];

		const idMap = {};
		const newNodes = [];
		const newEdges = [];
		const existingActionIds = new Set(
			(nodes.value || [])
				.map((node) => String(node?.data?.action_id || "").trim())
				.filter(Boolean)
		);
		const sanitizeId = (value) =>
			String(value || "")
				.trim()
				.replace(/\s+/g, "_")
				.replace(/[^\w-]/g, "_");
		const getUniqueActionId = (seed) => {
			const base = sanitizeId(seed) || generateShortId();
			if (!existingActionIds.has(base)) {
				existingActionIds.add(base);
				return base;
			}
			let index = 2;
			let candidate = `${base}_${index}`;
			while (existingActionIds.has(candidate)) {
				index += 1;
				candidate = `${base}_${index}`;
			}
			existingActionIds.add(candidate);
			return candidate;
		};

		// 1. Calculate bounding box of pasted nodes to find offset
		const minX = Math.min(...pastedNodes.map((n) => n.position?.x || 0));
		const minY = Math.min(...pastedNodes.map((n) => n.position?.y || 0));

		// 2. Map IDs and create new nodes
		pastedNodes.forEach((node) => {
			const oldId = node.id;
			const newId = generateShortId();
			idMap[oldId] = newId;

			// Deep clone
			const newNode = deepClone(node);
			newNode.id = newId;
			if (newNode.data) {
				const sourceActionId = newNode.data.action_id || oldId || newId;
				newNode.data.action_id = getUniqueActionId(sourceActionId);
				newNode.data.name = null; // Clear backend name to force new record
				// Ensure mandatory fields are at least present
				if (
					newNode.data.action_type === "Document Action" &&
					!newNode.data.permission_audit_reason
				) {
					newNode.data.permission_audit_reason = "System Rule Execution";
				}
			}

			// Shift position relative to paste point
			newNode.position = {
				x: (node.position?.x || 0) - minX + position.x,
				y: (node.position?.y || 0) - minY + position.y,
			};

			newNodes.push(newNode);
		});

		// 3. Remap next_step pointers in node data
		newNodes.forEach((node) => {
			if (node.data) {
				if (node.data.next_step_if_true && idMap[node.data.next_step_if_true]) {
					node.data.next_step_if_true = idMap[node.data.next_step_if_true];
				} else {
					node.data.next_step_if_true = null;
				}

				if (node.data.next_step_if_false && idMap[node.data.next_step_if_false]) {
					node.data.next_step_if_false = idMap[node.data.next_step_if_false];
				} else {
					node.data.next_step_if_false = null;
				}

				// ENSURE terminal nodes have no next steps
				if (isTerminalAction(node.data.action_type)) {
					node.data.next_step_if_true = null;
					node.data.next_step_if_false = null;
				}
			}
		});

		// 4. Create new edges for internal connections
		(pastedEdges || []).forEach((edge) => {
			if (idMap[edge.source] && idMap[edge.target]) {
				const newSourceId = idMap[edge.source];
				const newTargetId = idMap[edge.target];

				// DO NOT paste outgoing edges from terminal nodes
				const sourceNode = newNodes.find((n) => n.id === newSourceId);
				if (
					sourceNode?.data?.action_type &&
					isTerminalAction(sourceNode.data.action_type)
				) {
					return;
				}

				const newEdgeId = `e-${newSourceId}-${newTargetId}-${
					edge.sourceHandle || "default"
				}`;
				newEdges.push({
					...edge,
					id: newEdgeId,
					source: newSourceId,
					target: newTargetId,
				});
			}
		});

		// 5. Auto-scaffold missing paths for Condition/Switch
		newNodes.forEach((node) => {
			if (
				node.data &&
				(node.data.action_type === "Condition" || node.data.action_type === "Switch")
			) {
				if (!node.data.next_step_if_false) {
					const stopNodeId = generateShortId();
					const stopData = get_default_node_data("stop");
					stopData.operation = "Success";
					stopData.action_id = stopNodeId;

					const stopNode = {
						id: stopNodeId,
						type: "stop",
						position: {
							x: node.position.x + 100,
							y: node.position.y + 150,
						},
						label: __("End"),
						data: stopData,
					};

					node.data.next_step_if_false = stopNodeId;
					newNodes.push(stopNode);

					newEdges.push({
						id: `e-${node.id}-${stopNodeId}-false`,
						source: node.id,
						target: stopNodeId,
						sourceHandle: "false",
						type: "add",
					});
				}
			}
		});

		// 6. Add to store
		nodes.value = [...nodes.value, ...newNodes];
		edges.value = [...edges.value, ...newEdges];

		return newNodes;
	}

	function hasOutgoingEdge(nodeId) {
		return (edges.value || []).some((edge) => edge.source === nodeId);
	}

	function getAutoConnectSource(selectedId) {
		const selectedNode = (nodes.value || []).find((node) => node.id === selectedId);
		const selectedActionType = selectedNode?.data?.action_type || selectedNode?.type;
		if (
			selectedNode &&
			selectedNode.type !== "selector" &&
			selectedNode.type !== "condition" &&
			!isTerminalAction(selectedActionType) &&
			!hasOutgoingEdge(selectedNode.id)
		) {
			return selectedNode;
		}

		const startNode = (nodes.value || []).find(
			(node) => node.id === "start" || node.type === "start"
		);
		if (startNode && !hasOutgoingEdge(startNode.id)) {
			return startNode;
		}

		return null;
	}

	function autoConnectNode(nodeId, parentNode = null, selectedId = null) {
		const sourceNode = parentNode || getAutoConnectSource(selectedId);
		if (!sourceNode) return;

		const sourceHandle = sourceNode.type === "condition" ? null : "default";
		const edgeId = `e-${sourceNode.id}-${nodeId}-${sourceHandle || "default"}`;
		const exists = (edges.value || []).some(
			(edge) =>
				edge.source === sourceNode.id &&
				edge.target === nodeId &&
				(edge.sourceHandle || "default") === (sourceHandle || "default")
		);
		if (exists) return;

		edges.value = [
			...edges.value,
			{
				id: edgeId,
				source: sourceNode.id,
				target: nodeId,
				sourceHandle: sourceHandle || "default",
				type: "add",
				animated: sourceNode.type === "start",
			},
		];
	}

	function autoConnectStartNode() {
		const startNode = (nodes.value || []).find(
			(el) => el.id === "start" || el.type === "start"
		);
		if (!startNode) return;

		// Check if start node has any outgoing edges
		const hasStartEdge = (edges.value || []).some((el) => el.source === startNode.id);
		if (hasStartEdge) return;

		const firstNode = (nodes.value || []).find(
			(el) => el.type !== "start" && el.data?.is_enabled !== 0
		);
		if (firstNode) {
			edges.value.push({
				id: `e-${startNode.id}-${firstNode.id}`,
				source: startNode.id,
				target: firstNode.id,
				sourceHandle: "default",
				type: "add",
				animated: true,
			});
		}
	}

	return {
		// State
		nodes,
		edges,

		// Computed
		effectiveDisabledIds,

		// Snapshot
		getStateSnapshot,
		getGraphSnapshot,
		applyGraphSnapshot,

		// Topology
		getTopologicalSort,
		getAvailableVariables,
		getEffectivelyDisabledIds,

		// Node operations
		get_default_node_data,
		delete_node,
		delete_edge,
		touch_node,
		insert_node_on_edge,
		pasteNodes,
		paste_on_edge,
		toggle_node_enabled,

		// Sync
		sync_actions_to_graph,
		merge_visual_layout,
		update_node_position,
		get_visual_data_payload,
		initialize_default_graph,

		// Normalization + cleaning
		normalize_graph_nodes,
		normalize_action_data,
		clean_graph_data,
		clean_action_config,

		// Auto-connection
		hasOutgoingEdge,
		getAutoConnectSource,
		autoConnectNode,
		autoConnectStartNode,
	};
});
