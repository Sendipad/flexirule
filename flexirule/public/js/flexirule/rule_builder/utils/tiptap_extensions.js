import { Node, Mark, mergeAttributes } from "@tiptap/core";
import Mention from "@tiptap/extension-mention";
import { PluginKey } from "@tiptap/pm/state";
import { encodeData, decodeData } from "./text_generator";

export const VarPluginKey = new PluginKey("variableTrigger");
export const LogicPluginKey = new PluginKey("logicTrigger");

// ── Variable Node ──
export const VariableNode = Node.create({
	name: "variable",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			path: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-path") || el.innerText.replace(/^@/, ""),
				renderHTML: (attrs) => ({ "data-path": attrs.path }),
			},
			label: {
				default: "",
				parseHTML: (el) => el.getAttribute("data-label") || "",
				renderHTML: (attrs) => ({ "data-label": attrs.label }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-type="variable"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const displayText = node.attrs.label || node.attrs.path;
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-type": "variable",
				class: "tg-badge tg-badge-var",
			}),
			["i", { class: "fa fa-at mr-1" }],
			["span", displayText],
		];
	},
});

// ── Logic Node ──
// Represents IF/ELSE/END-IF and LOOP/END-LOOP badges inline.
// Key attributes stored in `data-logic-type` as base64-encoded JSON.
export const LogicNode = Node.create({
	name: "logic",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			type: {
				default: "conditional",
				parseHTML: (el) =>
					decodeData(el.getAttribute("data-logic-type")).type || "conditional",
			},
			_key: {
				default: null,
				parseHTML: (el) => decodeData(el.getAttribute("data-logic-type"))._key || null,
			},
			label: {
				default: "",
				parseHTML: (el) => decodeData(el.getAttribute("data-logic-type")).label || "",
			},
			isStart: {
				default: true,
				parseHTML: (el) => {
					const data = decodeData(el.getAttribute("data-logic-type"));
					if (typeof data.isStart === "boolean") return data.isStart;
					// Legacy fallback: infer from CSS class and text
					if (el.classList.contains("tg-badge-end")) return false;
					if (el.classList.contains("tg-badge-else")) return false;
					if (el.innerText.trim() === "}") return false;
					if (el.innerText.includes("ELSE")) return false;
					return true;
				},
			},
			isElse: {
				default: false,
				parseHTML: (el) => {
					const data = decodeData(el.getAttribute("data-logic-type"));
					if (typeof data.isElse === "boolean") return data.isElse;
					return el.classList.contains("tg-badge-else") || el.innerText.includes("ELSE");
				},
			},
			condition: {
				default: null,
				parseHTML: (el) => decodeData(el.getAttribute("data-logic-type")).condition || null,
			},
			_raw_expr: {
				default: "",
				parseHTML: (el) => decodeData(el.getAttribute("data-logic-type"))._raw_expr || "",
			},
			iterator: {
				default: "",
				parseHTML: (el) => decodeData(el.getAttribute("data-logic-type")).iterator || "",
			},
			iterable: {
				default: "",
				parseHTML: (el) => decodeData(el.getAttribute("data-logic-type")).iterable || "",
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-type="logic"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const { type, isStart, isElse, _key } = node.attrs;
		let label = "";
		let badgeClass = "tg-badge";
		let iconClass = "";

		if (isElse) {
			label = __("ELSE");
			badgeClass += " tg-badge-else";
			iconClass = "fa fa-code-fork";
		} else if (!isStart) {
			label = "}";
			badgeClass += " tg-badge-end";
		} else if (type === "conditional") {
			label = node.attrs.label ? __("IF {0}", [node.attrs.label]) : __("IF");
			badgeClass += " tg-badge-if";
			iconClass = "fa fa-code-fork";
		} else {
			label = node.attrs.label ? __("LOOP {0}", [node.attrs.label]) : __("LOOP");
			badgeClass += " tg-badge-loop";
			iconClass = "fa fa-refresh";
		}

		const data = encodeData({
			type,
			_key,
			isStart,
			isElse,
			label: node.attrs.label,
			condition: node.attrs.condition,
			_raw_expr: node.attrs._raw_expr,
			iterator: node.attrs.iterator,
			iterable: node.attrs.iterable,
		});

		// Logic for checking validation errors
		if (this.options.getValidationErrors) {
			const errors = this.options.getValidationErrors(_key);
			if (errors && errors.length > 0) {
				badgeClass += " is-invalid";
			}
		}

		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-type": "logic",
				"data-logic-type": data,
				class: badgeClass,
			}),
			iconClass ? ["i", { class: `${iconClass} mr-1` }] : "",
			["span", label],
		];
	},
});

// ── Mention-based trigger extensions ──
export const VariableTrigger = Mention.extend({
	name: "variableTrigger",
});

export const LogicTrigger = Mention.extend({
	name: "logicTrigger",
});

// ── Translation Mark ──
// Wraps inline text to compile as {{ _("text") }}
export const TranslationMark = Mark.create({
	name: "translation",
	addOptions() {
		return {
			HTMLAttributes: {
				class: "tg-badge tg-badge-trans",
				"data-type": "translation",
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-type="translation"]' }];
	},
	renderHTML({ HTMLAttributes }) {
		return ["span", mergeAttributes(this.options.HTMLAttributes, HTMLAttributes), 0];
	},
	addCommands() {
		return {
			setTranslation:
				() =>
				({ commands }) =>
					commands.setMark(this.name),
			toggleTranslation:
				() =>
				({ commands }) =>
					commands.toggleMark(this.name),
			unsetTranslation:
				() =>
				({ commands }) =>
					commands.unsetMark(this.name),
		};
	},
});
