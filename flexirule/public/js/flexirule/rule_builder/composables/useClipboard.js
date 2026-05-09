import { useVueFlow } from "@vue-flow/core";
import { useUIStore } from "../stores/useUIStore";
import { useGraphStore } from "../stores/useGraphStore";
import { useRuleStore } from "../stores/useRuleStore";

export function useClipboard() {
	const uiStore = useUIStore();
	const graphStore = useGraphStore();
	const ruleStore = useRuleStore();
	const { getSelectedNodes, getSelectedEdges, project } = useVueFlow();

	function stripNullValues(value) {
		if (Array.isArray(value)) {
			return value
				.map((item) => stripNullValues(item))
				.filter((item) => item !== null && item !== undefined);
		}
		if (value && typeof value === "object") {
			const cleaned = {};
			Object.entries(value).forEach(([key, val]) => {
				const nextVal = stripNullValues(val);
				if (nextVal !== null && nextVal !== undefined) {
					cleaned[key] = nextVal;
				}
			});
			return cleaned;
		}
		if (value === null || value === undefined) return null;
		return value;
	}

	async function copySelectedToClipboard() {
		const selectedNodes = getSelectedNodes.value;
		if (!selectedNodes.length) return;

		// Don't allow copying start node
		const filterNodes = selectedNodes.filter((n) => n.id !== "start" && n.type !== "start");
		if (!filterNodes.length) {
			frappe.show_alert(
				{ message: __("Start node cannot be copied"), indicator: "orange" },
				2
			);
			return;
		}

		const selectedEdges = getSelectedEdges.value || [];
		const selectedNodeIds = new Set(filterNodes.map((n) => n.id));

		// Include all internal edges between selected nodes, even when edges are not
		// manually selected in VueFlow (multi-node copy UX parity with Frappe copy intent).
		const inferredInternalEdges = (graphStore.edges || []).filter(
			(e) => selectedNodeIds.has(e.source) && selectedNodeIds.has(e.target)
		);
		const allSelectedEdges = [...selectedEdges, ...inferredInternalEdges].filter(
			(edge, index, arr) =>
				arr.findIndex(
					(e) =>
						e.source === edge.source &&
						e.target === edge.target &&
						(e.sourceHandle || "default") === (edge.sourceHandle || "default")
				) === index
		);

		// Map to clean objects to avoid circular references and VueFlow internal state
		const payload = {
			type: "flexirule-clipboard",
			version: 2,
			copied_at: frappe.datetime.now_datetime(),
			source: {
				doctype: "Rule",
				name: ruleStore.rule_name || null,
			},
			nodes: filterNodes.map((n) => {
				const nodeData = JSON.parse(JSON.stringify(n.data || {}));
				// Sync condition_json for Condition nodes if missing
				if (
					nodeData.action_type === "Condition" &&
					!nodeData.condition_json &&
					nodeData.config
				) {
					nodeData.condition_json = JSON.stringify(nodeData.config);
				}
				const cleanedData = stripNullValues(nodeData);
				return {
					id: n.id,
					action_id: cleanedData?.action_id || n.id,
					type: n.type,
					position: { ...n.position },
					label: n.label,
					data: cleanedData,
				};
			}),
			edges: allSelectedEdges.map((e) => ({
				id: e.id,
				source: e.source,
				target: e.target,
				sourceHandle: e.sourceHandle,
				targetHandle: e.targetHandle,
				data: stripNullValues(JSON.parse(JSON.stringify(e.data || {}))),
			})),
		};

		const payloadStr = JSON.stringify(payload);
		uiStore.local_clipboard = payloadStr;
		localStorage.setItem("flexirule-clipboard", payloadStr); // Cross-tab fallback

		try {
			// Prefer Frappe's clipboard helper when available.
			if (frappe?.utils?.copy_to_clipboard) {
				frappe.utils.copy_to_clipboard(payloadStr);
			} else if (navigator?.clipboard && window.isSecureContext) {
				await navigator.clipboard.writeText(payloadStr);
			} else {
				throw new Error("Clipboard API unavailable");
			}
			frappe.show_alert(
				{
					message: __("{0} node(s) copied", [String(filterNodes.length)]),
					indicator: "blue",
				},
				2
			);
		} catch (e) {
			// Fallback for insecure contexts or API failure
			const textArea = document.createElement("textarea");
			textArea.value = payloadStr;
			textArea.style.position = "fixed";
			textArea.style.left = "-9999px";
			textArea.style.top = "0";
			document.body.appendChild(textArea);
			textArea.focus();
			textArea.select();

			try {
				const successful = document.execCommand("copy");
				if (successful) {
					frappe.show_alert(
						{
							message: __("Nodes copied to clipboard (system fallback)"),
							indicator: "blue",
						},
						2
					);
				} else {
					throw new Error("execCommand copy failed");
				}
			} catch (err) {
				console.warn("FlexiRule: All clipboard copy methods failed", err);
				frappe.show_alert(
					{
						message: __(
							"Nodes copied to local session only (cross-browser copy failed)"
						),
						indicator: "orange",
					},
					3
				);
			}
			document.body.removeChild(textArea);
		}
	}

	async function pasteFromClipboard(mousePos, flowWrapper) {
		if (ruleStore.is_read_only) return;

		let payload = null;

		// 1. Try system clipboard
		try {
			if (navigator?.clipboard && window.isSecureContext) {
				const text = await navigator.clipboard.readText();
				const parsed = JSON.parse(text);
				if (parsed.type === "flexirule-clipboard") {
					payload = parsed;
				}
			}
		} catch (e) {
			console.warn("FlexiRule: System clipboard read failed, trying local fallback", e);
		}

		// 2. Fallback to local clipboard (Pinia or localStorage for cross-tab)
		if (!payload) {
			try {
				const local =
					localStorage.getItem("flexirule-clipboard") || uiStore.local_clipboard;
				if (local) {
					const parsed = JSON.parse(local);
					if (parsed.type === "flexirule-clipboard") {
						payload = parsed;
					}
				}
			} catch (e) {
				console.error("FlexiRule: Local clipboard fallback failed", e);
			}
		}

		if (!payload) {
			frappe.show_alert(
				{ message: __("Clipboard is empty or invalid"), indicator: "orange" },
				3
			);
			return;
		}

		// Calculate paste position: mouse position in flow coordinates
		// Fallback to center if mouse is outside canvas
		const bounds = flowWrapper.getBoundingClientRect();
		const flowX = mousePos.x - bounds.left;
		const flowY = mousePos.y - bounds.top;

		const position = project({ x: flowX, y: flowY });

		const newNodes = graphStore.pasteNodes(payload.nodes, payload.edges, position);

		if (newNodes.length) {
			// Select the first pasted node
			uiStore.selected_id = newNodes[0].id;
			frappe.show_alert({ message: __("Nodes pasted"), indicator: "green" }, 2);
		}
	}

	return {
		copySelectedToClipboard,
		pasteFromClipboard,
	};
}
