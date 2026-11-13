<template>
	<div
		ref="controlRef"
		class="fvc-wrap"
		:class="{
			'is-compact': compact,
			'is-disabled': disabled || isReadOnly,
			'has-error': invalid || (showValidation && !isValid),
		}"
		v-fxr-fieldname="context?.df?.fieldname || fieldname || null"
		@keydown.capture="onStaticKeydown"
	>
		<!-- ── Main Control Area ── -->
		<div
			class="fvc-main-field"
			:class="{
				'is-dynamic': isDynamicMode || !isStaticSupported,
				'is-static-link': !isDynamicMode && isLinkType,
				'is-multi-select': isMultiSelect,
			}"
			@click="onWrapClick"
		>
			<!-- Static Mode (via ControlFactory or MultiSelectList) -->
			<div v-if="!isDynamicMode && isStaticSupported" class="fvc-static-container flex-1">
				<MultiSelectList
					v-if="isMultiSelectInline"
					:df="staticDf"
					:modelValue="formattedMultiSelectValue"
					:documentType="isLinkType ? referenceDoctype : undefined"
					:options="isLinkType ? undefined : fieldOptions"
					:filters="context?.filters"
					:get_data="context?.df?.get_data || undefined"
					:allowCustomValue="true"
					displayMode="badges"
					:badgeCollapseAfter="2"
					:allowWrap="false"
					:hideLabel="true"
					class="flex-1 min-w-0 w-100"
					@update:modelValue="updateStaticValue"
				/>
				<ControlFactory
					v-else
					:df="staticDf"
					:modelValue="staticValue"
					:doc="doc"
					:engine="engine"
					:context="context"
					:options="isLinkType ? undefined : fieldOptions"
					:hideLabel="true"
					class="flex-1 min-w-0 w-100 static-control-factory"
					@update:modelValue="updateStaticValue"
				/>
			</div>

			<!-- Dynamic Mode (Tiptap Editor) -->
			<div v-show="isDynamicMode || !isStaticSupported" class="fvc-editor-container flex-1">
				<div class="fvc-editor-wrapper">
					<editor-content :editor="editor" class="fvc-tiptap-editor" />

					<!-- Contextual placeholder -->
					<div
						v-if="!isReadOnly && isEditorEmpty && !isEditorFocused"
						class="fvc-empty-placeholder"
					>
						{{ placeholder || __("Choose a field, variable, or resolver (@)...") }}
					</div>
					<div
						v-else-if="!isReadOnly && isEditorEmpty && isEditorFocused"
						class="fvc-focus-hint"
					>
						{{ placeholder || __("Type Value or @ for Variable or Resolver") }}
					</div>
				</div>
			</div>

			<!-- Mode Toggle Button -->
			<div v-if="isStaticSupported && !isReadOnly" class="fvc-mode-toggle-wrap">
				<button
					type="button"
					class="fvc-toggle-btn"
					:title="
						isDynamicMode
							? __('Switch to Static Value')
							: __('Switch to Expression / Formula')
					"
					@click.stop="toggleDynamicMode"
				>
					<i :class="isDynamicMode ? 'fa fa-keyboard-o' : 'fa fa-bolt'"></i>
				</button>
			</div>
		</div>

		<!-- Field-first source palette: fields and variables are available as soon as the operand is empty. -->
		<div
			v-if="isSourcePaletteVisible"
			class="fvc-source-palette"
			@mousedown.stop
		>
			<div class="fvc-source-palette__search">
				<i class="fa fa-search" aria-hidden="true"></i>
				<input
					ref="sourcePaletteInput"
					v-model="sourcePaletteQuery"
					type="search"
					:placeholder="__('Search fields and variables...')"
					:aria-label="__('Search fields and variables')"
					@keydown="handleSourcePaletteKeydown"
				/>
				<button
					type="button"
					class="fvc-source-palette__close"
					:title="__('Close')"
					:aria-label="__('Close')"
					@click="sourcePaletteOpen = false"
				>
					<i class="fa fa-times" aria-hidden="true"></i>
				</button>
			</div>
			<MentionList :items="sourcePaletteItems" :command="selectSourcePaletteItem" />
		</div>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", context?.df?.label || __("Field")) }}
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount, nextTick } from "vue";
import { Editor, EditorContent, VueRenderer, VueNodeViewRenderer } from "@tiptap/vue-3";
import { StarterKit } from "@tiptap/starter-kit";
import { Node, mergeAttributes } from "@tiptap/core";
import Mention from "@tiptap/extension-mention";
import { PluginKey } from "@tiptap/pm/state";
import tippy from "tippy.js";

import {
	getCommandsForFieldtype,
	getFormulasForFieldtype,
	getAllowedBuilderKinds,
	getFunctionIcon,
} from "../../core/formula_registry";
import { compileToCode, compileToLabel } from "../../core/builder_utils.js";
import MentionList from "./MentionList.vue";
import ControlFactory from "./ControlFactory.vue";
import MultiSelectList from "./MultiSelectList.vue";
import ResolverTokenView from "./ResolverTokenView.vue";
import { resolveStaticPresentation } from "./static_presentation_policy.mjs";
import { parseListElements } from "./flexvalue_serialization.mjs";
import { buildSourceCatalogue, searchSourceCatalogue } from "./source_catalogue.mjs";
import { getAllStrategies } from "./value_resolver/strategies.js";
import { adaptStrategiesForCatalogue } from "./resolver_catalogue_adapter.mjs";

const props = defineProps({
	modelValue: { type: [Object, String, Number, Boolean], default: null },
	fieldname: String,
	doctype: { type: String, default: "" },
	variableOptions: { type: Array, default: () => [] },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
	compact: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	engine: { type: Object, default: null },
	doc: { type: Object, default: null },
	showValidation: { type: Boolean, default: false },
	invalid: { type: Boolean, default: false },
	context: { type: Object, default: () => ({}) },
	staticPresentation: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue", "update"]);

const isReadOnly = computed(() => !!props.readOnly || !!props.read_only);
const resolvedStaticConfig = computed(() => {
	return resolveStaticPresentation({
		staticPresentation: props.staticPresentation,
		context: props.context,
		fieldType: fieldType.value,
		fieldOptions: fieldOptions.value,
		referenceDoctype: referenceDoctype.value,
	});
});

const isMultiSelect = computed(() => resolvedStaticConfig.value.isMultiSelect);
const isMultiSelectInline = computed(() => resolvedStaticConfig.value.isMultiSelect);

const formattedMultiSelectValue = computed(() => {
	if (Array.isArray(staticValue.value)) {
		return staticValue.value.map(String);
	}
	if (typeof staticValue.value === "string" && staticValue.value.trim().length > 0) {
		return staticValue.value
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
	}
	return [];
});
const isDynamicMode = ref(false);
const isEditorFocused = ref(false);
const isSuggestionOpen = ref(false);
const activeTippyPopups = [];
const uid =
	Math.random().toString(36).substring(2, 15) + "_" + Math.random().toString(36).substring(2, 15);

const controlRef = ref(null);

const sourceCatalogue = computed(() => {
	const rawStrategies = getAllStrategies();
	const adaptedResolvers = adaptStrategiesForCatalogue(rawStrategies, {
		context: resolverContext.value,
		doctype: triggerDoctype.value,
		fieldType: fieldType.value,
	});
	return buildSourceCatalogue({
		docFields: props.docFields,
		variableOptions: availableVariableOptions.value,
		resolvers: adaptedResolvers,
		fieldType: fieldType.value,
		allowedResolverKinds: allowedBuilderKinds.value,
		currentDocType: triggerDoctype.value,
	});
});

function resolveResolverOutputType(family, operation) {
	const resolverSpecs = props.context?.conditionContract?.flexvalue_modes?.resolver;
	if (Array.isArray(resolverSpecs)) {
		const spec = resolverSpecs.find(
			(entry) => entry.family === family && entry.operation === operation
		);
		if (spec?.output_type) return spec.output_type;
	}
	return fieldType.value || "Data";
}

// Static Mode Helpers
const staticValue = ref("");

const fieldType = computed(() => props.context?.df?.fieldtype || "Data");
const fieldOptions = computed(() => {
	const options = props.context?.df?.options || [];
	const operator = String(props.context?.operator || "").toLowerCase();
	if (fieldType.value === "Check" && ["in", "not_in"].includes(operator)) {
		return [
			[1, __("Yes")],
			[0, __("No")],
		];
	}
	return options;
});
const referenceDoctype = computed(() => {
	const opts = fieldOptions.value;

	if (fieldType.value === "Link" && opts) {
		return opts;
	}

	if (fieldType.value === "Dynamic Link") {
		// Dynamic Link.options names the field containing the target DocType; it is
		// not itself a DocType. Resolve that field's current value when available.
		const targetField = typeof opts === "string" ? opts.trim() : "";
		const documentSources = [
			props.doc,
			props.context?.doc,
			props.engine?.doc,
			props.engine?.rule_doc,
		];
		for (const source of documentSources) {
			const value = targetField && source && typeof source === "object" ? source[targetField] : null;
			if (typeof value === "string" && value.trim()) return value.trim();
		}

		const controlContext = props.context?.controlContext;
		const contextValue =
			targetField && typeof controlContext?.getFieldValue === "function"
				? controlContext.getFieldValue(targetField)
				: null;
		if (contextValue && typeof contextValue === "object" && contextValue.mode === "static") {
			return String(contextValue.value || "");
		}
		if (typeof contextValue === "string" && contextValue.trim()) return contextValue.trim();
		return props.context?.dynamicDoctype || "";
	}

	if (opts && typeof opts === "string" && props.context?.filters) {
		const filterVal = props.context.filters[opts];
		if (filterVal !== undefined && filterVal !== null) {
			if (typeof filterVal === "object" && filterVal.mode === "static") {
				return String(filterVal.value || "");
			}
			if (typeof filterVal === "string") {
				return filterVal;
			}
		}
	}

	return props.context?.referenceDoctype || (Array.isArray(opts) ? "" : opts || "");
});

const triggerDoctype = computed(() => {
	return (
		props.doctype ||
		props.context?.currentDocType ||
		props.context?.triggerDoctype ||
		props.context?.doctype ||
		props.engine?.rule_doc?.document_type ||
		""
	);
});

const resolverContext = computed(() => {
	const df = props.context?.df || {};
	const fieldname = props.context?.fieldname || df.fieldname || df.value || "";
	return {
		...props.context,
		df,
		fieldname,
		target: props.context?.target || fieldname,
		referenceDoctype: referenceDoctype.value,
		triggerDoctype: triggerDoctype.value,
	};
});

const isLinkType = computed(() => {
	const ft = fieldType.value;
	return (
		ft === "Link" || ft === "Dynamic Link" || ft === "MultiSelectList" || ft === "MultiSelect"
	);
});

const PURE_TEXT_FIELDTYPES = new Set(["Code", "Text Editor", "JSON"]);

const isStaticSupported = computed(() => {
	if (isMultiSelect.value) return true;
	return !PURE_TEXT_FIELDTYPES.has(fieldType.value);
});

const RESOLVER_LEVEL_KIND_MAP = {
	basic: ["system_context", "text"],
	standard: ["date_time", "system_context", "text"],
	advanced: ["date_time", "math_formula", "collection", "system_context", "text"],
	full: null,
};

const configuredResolverLevel = computed(() => {
	return String(
		props.context?.resolverLevel ||
			props.context?.allowedResolverLevel ||
			props.engine?.settings?.value_resolver_level ||
			props.engine?.settings?.resolver_level ||
			"full"
	)
		.toLowerCase()
		.trim();
});

const availableVariableOptions = computed(() => {
	let options = Array.isArray(props.variableOptions) ? [...props.variableOptions] : [];

	if (typeof props.context?.getVariableOptions === "function") {
		options = props.context.getVariableOptions(options, {
			fieldType: fieldType.value,
			context: props.context,
		});
	}

	if (typeof props.context?.filterVariableOptions === "function") {
		options = options.filter((item) =>
			props.context.filterVariableOptions(item, {
				fieldType: fieldType.value,
				context: props.context,
			})
		);
	}

	return Array.isArray(options) ? options : [];
});

const allowedBuilderKinds = computed(() => {
	let kinds =
		Array.isArray(props.context?.allowedKinds) && props.context.allowedKinds.length
			? [...props.context.allowedKinds]
			: getAllowedBuilderKinds(fieldType.value);

	if (typeof props.context?.getAllowedKinds === "function") {
		kinds = props.context.getAllowedKinds(kinds, {
			fieldType: fieldType.value,
			context: props.context,
		});
	}

	const levelKinds = RESOLVER_LEVEL_KIND_MAP[configuredResolverLevel.value];
	if (Array.isArray(levelKinds)) {
		if (Array.isArray(kinds)) {
			kinds = kinds.filter((kind) => levelKinds.includes(kind));
		} else {
			kinds = [...levelKinds];
		}
	}

	return Array.isArray(kinds) && kinds.length ? kinds : null;
});

const staticDf = computed(() => {
	const cfg = resolvedStaticConfig.value;
	let ft = fieldType.value || "Data";
	let opts = cfg.options;

	if (cfg.control === "link") {
		ft = "Link";
		opts = cfg.doctype || referenceDoctype.value;
	} else if (cfg.control === "select") {
		ft = "Select";
	} else if (cfg.control === "multi-select") {
		ft = "MultiSelect";
	} else if (cfg.control === "input") {
		// Preserve native fieldtype (e.g. Int, Float, Currency, Percent, Check, Date, Datetime, Time)
		// rather than coercing everything to Data!
		ft = fieldType.value || "Data";
	}

	return {
		...props.context?.df,
		fieldtype: ft,
		label: "",
		options: opts,
		read_only: props.disabled || isReadOnly.value,
		placeholder: cfg.placeholder || props.placeholder,
	};
});

// ── Tiptap Extensions ──

const VariableToken = Node.create({
	name: "variableToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			path: {
				default: "",
				parseHTML: (element) =>
					element.getAttribute("data-path") || element.getAttribute("path") || "",
				renderHTML: (attrs) => ({ "data-path": attrs.path || "" }),
			},
			label: {
				default: "",
				parseHTML: (element) =>
					element.getAttribute("data-label") || element.getAttribute("label") || "",
				renderHTML: (attrs) => ({ "data-label": attrs.label || "" }),
			},
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="variable"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "variable",
				class: "token-chip token-variable",
			}),
			`👤 ${node.attrs.label || node.attrs.path}`,
		];
	},
});

const ResolverToken = Node.create({
	name: "resolverToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,

	addOptions() {
		return {
			doctype: "",
			readOnly: false,
			context: {},
		};
	},

	addAttributes() {
		return {
			expression: { default: "" },
			label: { default: "" },
			family: { default: "" },
			operation: { default: "" },
			value_type: { default: "" },
			config: { default: null },
			resolver: { default: "" },
			autoOpen: { default: false },
		};
	},

	parseHTML() {
		const getAttrs = (dom) => {
			const configRaw = dom.getAttribute("data-config");
			let config = null;
			if (configRaw) {
				try {
					config = JSON.parse(configRaw);
				} catch (e) {
					config = null;
				}
			}
			return {
				expression: dom.getAttribute("data-expression") || "",
				resolver: dom.getAttribute("data-resolver") || "",
				label: dom.getAttribute("data-label") || "",
				family: dom.getAttribute("data-family") || "",
				operation: dom.getAttribute("data-operation") || "",
				config: config,
			};
		};
		return [
			{ tag: 'span[data-token-type="resolver"]', getAttrs },
			{ tag: 'span[data-token-type="formula"]', getAttrs },
			{ tag: 'span[data-token-type="normalize"]', getAttrs },
			{ tag: 'span[data-token-type="format"]', getAttrs },
		];
	},

	renderHTML({ node, HTMLAttributes }) {
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "resolver",
				"data-config": JSON.stringify(node.attrs.config),
				"data-family": node.attrs.family || "",
				"data-operation": node.attrs.operation || "",
				"data-expression": node.attrs.expression,
				"data-label": node.attrs.label,
			}),
			0,
		];
	},

	addNodeView() {
		return VueNodeViewRenderer(ResolverTokenView);
	},
});

function createSuggestionRenderer() {
	let component;
	let popup;
	return {
		onStart: (props) => {
			isSuggestionOpen.value = true;
			activeTippyPopups.forEach((p) => {
				if (p) {
					if (Array.isArray(p)) {
						p.forEach((pi) => pi?.destroy?.());
					} else if (typeof p.destroy === "function") {
						p.destroy();
					}
				}
			});
			activeTippyPopups.length = 0;

			component = new VueRenderer(MentionList, { props, editor: props.editor });
			if (!props.clientRect) return;
			popup = tippy(document.createElement("div"), {
				getReferenceClientRect: props.clientRect,
				appendTo: () => document.body,
				content: component.element,
				showOnCreate: true,
				interactive: true,
				trigger: "manual",
				placement: "bottom-start",
				zIndex: 14000,
			});
			activeTippyPopups.push(popup);
		},
		onUpdate(props) {
			component?.updateProps(props);
			if (!props.clientRect) return;
			popup?.setProps({ getReferenceClientRect: props.clientRect });
		},
		onKeyDown(props) {
			if (props.event.key === "Escape") {
				props.event.preventDefault();
				props.event.stopPropagation();
				props.event.stopImmediatePropagation();
				popup?.hide();
				return true;
			}
			return component?.ref?.onKeyDown(props);
		},
		onExit() {
			isSuggestionOpen.value = false;
			if (popup) {
				try {
					popup.destroy();
				} catch (e) {}
				const idx = activeTippyPopups.indexOf(popup);
				if (idx > -1) activeTippyPopups.splice(idx, 1);
				popup = null;
			}
			if (component) {
				try {
					component.destroy();
				} catch (e) {}
				component = null;
			}
		},
	};
}

let lastEmittedJSON = "";

const VariableTrigger = Mention.extend({ name: `variableTrigger_${uid}` });
const CommandTrigger = Mention.extend({ name: `commandTrigger_${uid}` });

const editor = new Editor({
	extensions: [
		StarterKit.configure({
			heading: false,
			codeBlock: false,
			blockquote: false,
			bulletList: false,
			orderedList: false,
			listItem: false,
			horizontalRule: false,
		}),
		VariableToken,
		ResolverToken.configure({
			doctype: triggerDoctype.value,
			readOnly: isReadOnly.value,
			context: resolverContext.value,
		}),
		VariableTrigger.configure({
			suggestion: {
				char: "@",
				pluginKey: new PluginKey(`variableTrigger_${uid}`),
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					return searchSourceCatalogue(sourceCatalogue.value, query, {
						preferredFieldType: fieldType.value,
						isLeftOperand: !!props.context?.isLeftOperand,
						conditionContract: props.context?.conditionContract || null,
						scopeStack:
							props.context?.scopeStack || props.context?.activeIterators || [],
					}).slice(0, 25);
				},
				command: ({ editor, range, props }) => {
					if (props.sourceType === "resolver") {
						editor
							.chain()
							.focus()
							.insertContentAt(range, [
								{
									type: "resolverToken",
									attrs: {
										family: props.family,
										operation: props.operation,
										value_type: resolveResolverOutputType(props.family, props.operation),
										config: props.payload?.config || {},
										label: props.primaryLabel,
										autoOpen: true,
									},
								},
							])
							.run();
					} else {
						editor
							.chain()
							.focus()
							.insertContentAt(range, [
								{
									type: "variableToken",
									attrs: {
										path: props.canonicalPath || props.id,
										label: props.primaryLabel || props.label,
									},
								},
							])
							.run();
					}
				},
			},
		}),
		CommandTrigger.configure({
			suggestion: {
				char: "/",
				pluginKey: new PluginKey(`commandTrigger_${uid}`),
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					// Use canonical resolvers from sourceCatalogue, filtered by search query
					const resolvers = sourceCatalogue.value.filter(
						(i) => i.sourceType === "resolver"
					);
					const results = searchSourceCatalogue(resolvers, query, {
						preferredFieldType: fieldType.value,
						isLeftOperand: !!props.context?.isLeftOperand,
						allowedResolverOperandsOnly: !!props.context?.isLeftOperand,
						conditionContract: props.context?.conditionContract || null,
					});

					// Add standard clear utility
					if (!query || "clear".includes(query.toLowerCase())) {
						results.push({
							id: "clear",
							sourceType: "command",
							category: "commands",
							categoryLabel: __("Commands"),
							icon: "fa fa-trash",
							primaryLabel: __("Clear"),
							rawLabel: "Clear",
							secondaryText: __("Clear input content"),
						});
					}
					return results.slice(0, 25);
				},
				command: ({ editor, range, props }) => {
					if (props.id === "clear") {
						editor.chain().focus().setContent("").run();
						return;
					}

					// Insert full canonical resolver payload
					editor
						.chain()
						.focus()
						.insertContentAt(range, [
							{
								type: "resolverToken",
								attrs: {
									family: props.family,
									operation: props.operation,
									value_type: resolveResolverOutputType(props.family, props.operation),
									config: props.payload?.config || {},
									label: props.primaryLabel,
									autoOpen: true,
								},
							},
						])
						.run();
				},
			},
		}),
	],
	editable: !isReadOnly.value,
	editorProps: {
		handleKeyDown(view, event) {
			if (event.key === "Enter") {
				if (isSuggestionOpen.value) return false;
				event.preventDefault();
				emit("submit");
				return true;
			}
			return false;
		},
		transformPastedText(text) {
			return text.replace(/[\r\n]+/g, " ");
		},
	},
	onUpdate: () => {
		emitChanges();
	},
	onFocus: () => {
		isEditorFocused.value = true;
	},
	onBlur: () => {
		isEditorFocused.value = false;
	},
});

const isEditorEmpty = computed(() => editor.isEmpty);

const isValid = computed(() => {
	if (!props.context?.df?.reqd) return true;
	const struct = coerceStructuredValue(serialize());
	if (struct.mode === "static") {
		if (Array.isArray(struct.value)) {
			return (
				struct.value.length > 0 &&
				struct.value.every(
					(value) =>
						value !== undefined &&
						value !== null &&
						!(typeof value === "string" && value.trim() === "")
				)
			);
		}
		if (typeof struct.value === "string") return struct.value.trim() !== "";
		return struct.value !== undefined && struct.value !== null && struct.value !== "";
	}
	if (struct.mode === "variable") return !!(struct.path?.scope && struct.path?.segments?.length);
	if (struct.mode === "resolver") {
		return (
			!!(
				struct.family &&
				struct.operation &&
				struct.config &&
				typeof struct.config === "object"
			) || !!struct.value
		);
	}
	if (struct.mode === "template")
		return Array.isArray(struct.segments) && struct.segments.length > 0;
	if (struct.mode === "expression") return Array.isArray(struct.value) && struct.value.length > 0;
	return true;
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} is required").replace("{0}", props.context?.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

// ── Serialization ──

function coerceStructuredValue(val) {
	const currentFieldType = fieldType.value || "Data";

	if (val && typeof val === "object" && val.mode) {
		if (["formula", "format", "normalize", "normalization"].includes(val.mode)) {
			const config = { ...(val.config || {}) };
			let fam = val.family || config.family;
			let op = val.operation || config.operation;

			if (!fam || !op) {
				if (val.mode === "formula") {
					if (config.kind === "date_time" || config.base_type || config.offset_unit) {
						fam = "date_time";
						op = "calculate";
					} else if (config.str_op || config.kind === "text") {
						fam = "text";
						op = "combine";
					} else {
						fam = "math";
						op = "formula";
					}
				} else if (["normalize", "normalization"].includes(val.mode)) {
					fam = "text";
					op = "normalize";
				} else if (val.mode === "format") {
					if (config.fmt_op === "format_date" || config.kind === "date_time") {
						fam = "date_time";
						op = "format";
					} else {
						fam = "text";
						op = "format";
					}
				}
			}

			return {
				mode: "resolver",
				family: fam || "text",
				operation: op || "combine",
				value_type: val.value_type || currentFieldType,
				config: config.config && typeof config.config === "object" ? config.config : config,
			};
		}
		if (val.mode === "variable") {
			if (val.path && typeof val.path === "object") {
				const scope = val.path.scope || "doc";
				const segments = Array.isArray(val.path.segments) ? [...val.path.segments] : [];
				return {
					mode: "variable",
					path: { scope, segments },
				};
			}
			const pathStr = String(val.path || val.value || "");
			const parts = pathStr.split(".");
			const scope = parts[0] || "doc";
			const segments = parts.slice(1);
			return {
				mode: "variable",
				path: { scope, segments },
			};
		}
		if (val.mode === "resolver") {
			const rawConfig = val.config || {};
			let family = val.family || rawConfig.family;
			let operation = val.operation || rawConfig.operation;
			let config = rawConfig;

			if (!family) {
				if (rawConfig.kind === "math_formula") {
					family = "math";
					operation = operation || "formula";
				} else if (
					rawConfig.kind === "collection" ||
					rawConfig.kind === "child_aggregation"
				) {
					family = "collection";
					operation = operation || rawConfig.operation || rawConfig.agg_op || "any";
				} else if (rawConfig.kind === "lookup" || rawConfig.kind === "fetch") {
					family = "lookup";
					operation = operation || "fetch";
				} else if (rawConfig.kind === "system_context") {
					family = "system_context";
					operation = operation || "get";
				} else if (rawConfig.kind) {
					family = rawConfig.kind;
				}
			}

			if (config.config && typeof config.config === "object") {
				config = config.config;
			}

			return {
				mode: "resolver",
				family: family || "text",
				operation: operation || "combine",
				value_type: val.value_type || currentFieldType,
				config,
			};
		}
		if (val.mode === "template") {
			return { mode: "template", segments: Array.isArray(val.segments) ? val.segments : [] };
		}
		if (val.mode === "expression") {
			return { mode: "expression", value: Array.isArray(val.value) ? val.value : [] };
		}
		return {
			mode: "static",
			value_type: val.value_type || currentFieldType,
			value: val.value,
		};
	}

	if (val === null || val === undefined) {
		return { mode: "static", value_type: currentFieldType, value: "" };
	}
	return { mode: "static", value_type: currentFieldType, value: val };
}

function serialize() {
	const currentFieldType = fieldType.value || "Data";

	if (editor.isEmpty && !isDynamicMode.value) {
		if (isMultiSelect.value) {
			const parsedItems = parseListElements(staticValue.value, currentFieldType);
			return {
				mode: "static",
				value_type: "list",
				value: parsedItems,
			};
		}
		return {
			mode: "static",
			value_type: currentFieldType,
			value: staticValue.value,
		};
	}

	const doc = editor.getJSON();
	const content = doc.content?.[0]?.content || [];

	if (content.length === 0) {
		return { mode: "static", value_type: currentFieldType, value: "" };
	}

	if (content.length === 1 && content[0].type !== "text") {
		const node = content[0];
		const typeName = node.type.name || node.type;
		if (typeName === "variableToken") {
			const rawPath = String(node.attrs.path || "");
			const parts = rawPath.split(".");
			const scope = parts[0] || "doc";
			const segments = parts.slice(1);
			return {
				mode: "variable",
				path: { scope, segments },
			};
		}
		if (typeName === "resolverToken") {
			const config = node.attrs.config || {};
			const family =
				node.attrs.family ||
				config.family ||
				(config.kind === "math_formula" ? "math" : config.kind) ||
				"text";
			const operation =
				node.attrs.operation ||
				config.operation ||
				(family === "math" ? "formula" : config.kind === "lookup" ? "fetch" : "combine");
			const innerConfig =
				config.config && typeof config.config === "object" ? config.config : config;
			return {
				mode: "resolver",
				family,
				operation,
				value_type: node.attrs.value_type || currentFieldType,
				config: innerConfig,
			};
		}
	}

	const segments = content.map((item) => {
		const typeName = item.type?.name || item.type;
		if (typeName === "text") {
			return { type: "text", value: item.text || "" };
		}
		if (typeName === "variableToken") {
			const rawPath = String(item.attrs.path || "");
			const parts = rawPath.split(".");
			const scope = parts[0] || "doc";
			const segs = parts.slice(1);
			return {
				type: "value",
				value: {
					mode: "variable",
					path: { scope, segments: segs },
				},
			};
		}
		if (typeName === "resolverToken") {
			const cfg = item.attrs.config || {};
			const fam =
				item.attrs.family ||
				cfg.family ||
				(cfg.kind === "math_formula" ? "math" : cfg.kind) ||
				"text";
			const op =
				item.attrs.operation ||
				cfg.operation ||
				(fam === "math" ? "formula" : cfg.kind === "lookup" ? "fetch" : "combine");
			const innerCfg = cfg.config && typeof cfg.config === "object" ? cfg.config : cfg;
			return {
				type: "value",
				value: {
					mode: "resolver",
					family: fam,
					operation: op,
					value_type: item.attrs.value_type || currentFieldType,
					config: innerCfg,
				},
			};
		}
		return { type: "text", value: "" };
	});

	return { mode: "template", segments };
}

function escapeAttr(str) {
	return String(str || "")
		.replace(/&/g, "&amp;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
}

function isVariableSyntax(val) {
	return (
		typeof val === "string" &&
		(val.startsWith("@") || val.startsWith("doc.") || val.startsWith("vars."))
	);
}

function deserialize(val) {
	if (!val) return "";
	const structured = coerceStructuredValue(val);

	if (structured.mode === "variable") {
		const path = structured.path;
		let displayPath = "";
		if (typeof path === "string") {
			displayPath = path.trim();
		} else if (path && typeof path === "object" && typeof path.scope === "string") {
			const segments = Array.isArray(path.segments)
				? path.segments.filter(
						(segment) => typeof segment === "string" && segment.length > 0
				  )
				: [];
			if (segments.length) displayPath = path.scope + "." + segments.join(".");
			else if (path.scope === "doctype") displayPath = "doctype";
		}
		if (!displayPath) return "";
		return `<span data-token-type="variable" data-path="${escapeAttr(
			displayPath
		)}" data-label=""></span>`;
	}

	if (structured.mode === "resolver") {
		return `<span data-token-type="resolver" data-family="${escapeAttr(
			structured.family || ""
		)}" data-operation="${escapeAttr(
			structured.operation || ""
		)}" data-expression="${escapeAttr(
			structured.value || ""
		)}" data-label="" data-config='${escapeAttr(
			JSON.stringify(structured.config || null)
		)}'></span>`;
	}

	if (structured.mode === "template" && Array.isArray(structured.segments)) {
		return structured.segments
			.map((segment) => {
				if (!segment || typeof segment !== "object") return "";
				if (segment.type === "text") return segment.value || "";
				if (segment.type === "value" && segment.value) {
					return deserialize(segment.value);
				}
				return "";
			})
			.join("");
	}

	if (structured.mode === "expression" && Array.isArray(structured.value)) {
		return structured.value
			.map((item) => {
				const typeName = item.type?.name || item.type;
				if (typeName === "text") return item.value;
				if (typeName === "variableToken")
					return `<span data-token-type="variable" data-path="${escapeAttr(
						item.attrs.path
					)}" data-label="${escapeAttr(item.attrs.label)}"></span>`;
				if (
					["resolverToken", "formulaToken", "normalizeToken", "formatToken"].includes(
						typeName
					)
				) {
					return `<span data-token-type="resolver" data-expression="${escapeAttr(
						item.attrs.expression || item.attrs.resolver || ""
					)}" data-label="${escapeAttr(
						item.attrs.label || ""
					)}" data-config='${escapeAttr(
						JSON.stringify(item.attrs.config || null)
					)}'></span>`;
				}
				return "";
			})
			.join("");
	}

	return structured.value ?? "";
}

function emitChanges() {
	const output = coerceStructuredValue(serialize());
	const json = JSON.stringify(output);

	if (json === lastEmittedJSON) return;
	lastEmittedJSON = json;
	emit("update:modelValue", output);
	emit("update", output);
	try {
		if (typeof props.context?.onUpdate === "function") {
			props.context.onUpdate(output);
		}
		if (typeof props.context?.onChange === "function") {
			props.context.onChange(output);
		}
	} catch (error) {
		console.warn("FlexValueControl context callback failed:", error);
	}
}

// ── Orchestration ──

function onWrapClick() {
	if (isFieldFirst.value && isEditorEmpty.value && !isReadOnly.value && !props.disabled) {
		sourcePaletteOpen.value = true;
		return;
	}
	if (isDynamicMode.value || !isStaticSupported.value) editor.commands.focus();
}

function toggleDynamicMode() {
	if (isReadOnly.value || props.disabled) return;
	if (isDynamicMode.value) {
		const struct = serialize();
		if (struct.mode === "static") {
			isDynamicMode.value = false;
			staticValue.value = struct.value ?? "";
			emitChanges();
		}
	} else {
		isDynamicMode.value = true;
		const prev = staticValue.value;
		lastEmittedJSON = "";
		editor.commands.setContent(prev != null ? String(prev) : "");
		nextTick(() => editor.commands.focus());
	}
}

function onStaticKeydown(e) {
	if (isReadOnly.value || props.disabled || isDynamicMode.value || !isStaticSupported.value)
		return;
	if (e.key === "@" || e.key === "/") {
		e.preventDefault();
		e.stopPropagation();
		isDynamicMode.value = true;
		lastEmittedJSON = "";
		nextTick(() => {
			editor.commands.setContent("");
			editor.commands.focus();
			editor.commands.insertContent(e.key);
		});
	}
}

function updateStaticValue(val) {
	if (isVariableSyntax(val)) {
		const path = val.startsWith("@") ? val.substring(1) : val;
		isDynamicMode.value = true;
		lastEmittedJSON = "";
		nextTick(() => {
			editor.commands.setContent("");
			editor.commands.insertContent({
				type: "variableToken",
				attrs: { path, label: path },
			});
		});
		return;
	}
	staticValue.value = val;
	emitChanges();
}

const isFieldFirst = computed(() => {
	return !!(
		props.context?.isLeftOperand ||
		props.context?.fieldFirst ||
		props.staticPresentation?.fieldFirst
	);
});

const sourcePaletteOpen = ref(false);
const sourcePaletteQuery = ref("");
const sourcePaletteInput = ref(null);

const sourcePaletteItems = computed(() =>
	searchSourceCatalogue(sourceCatalogue.value, sourcePaletteQuery.value, {
		preferredFieldType: fieldType.value,
		isLeftOperand: true,
		conditionContract: props.context?.conditionContract || null,
		scopeStack: props.context?.scopeStack || props.context?.activeIterators || [],
	}).slice(0, 50)
);

const isSourcePaletteVisible = computed(
	() =>
		isFieldFirst.value &&
		sourcePaletteOpen.value &&
		isEditorEmpty.value &&
		!isReadOnly.value &&
		!props.disabled
);

watch(isSourcePaletteVisible, (visible) => {
	if (visible) nextTick(() => sourcePaletteInput.value?.focus());
});

watch(
	[isFieldFirst, isEditorEmpty, isReadOnly, () => props.disabled],
	([fieldFirst, empty, readOnly, disabled]) => {
		if (fieldFirst && empty && !readOnly && !disabled) {
			sourcePaletteOpen.value = true;
		} else {
			sourcePaletteOpen.value = false;
			sourcePaletteQuery.value = "";
		}
	},
	{ immediate: true }
);

function handleSourcePaletteKeydown(event) {
	if (event.key === "Escape") {
		event.preventDefault();
		sourcePaletteOpen.value = false;
		return;
	}
	if (event.key === "Enter" && sourcePaletteItems.value.length) {
		event.preventDefault();
		selectSourcePaletteItem(sourcePaletteItems.value[0]);
	}
}

function selectSourcePaletteItem(item) {
	if (!item || isReadOnly.value || props.disabled) return;

	const editorChain = editor.chain().focus().clearContent();
	if (item.sourceType === "resolver") {
		const family = item.family || item.payload?.family || "";
		const operation = item.operation || item.payload?.operation || "";
		editorChain
			.insertContent({
				type: "resolverToken",
				attrs: {
					family,
					operation,
					value_type: resolveResolverOutputType(family, operation),
					config: item.payload?.config || {},
					label: item.primaryLabel || item.rawLabel || family + "." + operation,
					autoOpen: true,
				},
			})
			.run();
	} else {
		const canonicalPath = item.canonicalPath || item.id;
		editorChain
			.insertContent({
				type: "variableToken",
				attrs: {
					path: canonicalPath,
					label: item.primaryLabel || item.rawLabel || canonicalPath,
				},
			})
			.run();
	}

	sourcePaletteOpen.value = false;
	sourcePaletteQuery.value = "";
}

watch(
	() => props.modelValue,
	(val) => {
		const normalized = coerceStructuredValue(val);
		const json = JSON.stringify(normalized);
		if (json === lastEmittedJSON && isDynamicMode.value === (normalized.mode !== "static"))
			return;
		if (normalized.mode !== "static") {
			isDynamicMode.value = true;
			editor.commands.setContent(deserialize(normalized));
			lastEmittedJSON = json;
		} else {
			// In field-first mode with an empty or unset value, present the dynamic field selector
			if (
				isFieldFirst.value &&
				(normalized.value === "" ||
					normalized.value === null ||
					normalized.value === undefined)
			) {
				isDynamicMode.value = true;
				editor.commands.setContent("");
			} else {
				isDynamicMode.value = false;
				staticValue.value = normalized.value ?? "";
			}
			lastEmittedJSON = json;
		}
	},
	{ immediate: true, deep: true }
);

onBeforeUnmount(() => {
	activeTippyPopups.forEach((popup) => {
		if (popup) {
			if (Array.isArray(popup)) {
				popup.forEach((p) => p?.destroy?.());
			} else if (typeof popup.destroy === "function") {
				popup.destroy();
			}
		}
	});
	activeTippyPopups.length = 0;
	editor.destroy();
});
</script>

<style scoped>
.fvc-wrap {
	display: flex;
	flex-direction: column;
	width: 100%;
	position: relative;
}

.fvc-source-palette {
	position: absolute;
	top: calc(var(--fxr-input-height, 32px) + 6px);
	left: 0;
	width: min(440px, 96vw);
	max-width: 100%;
	max-height: min(440px, 65vh);
	overflow: hidden;
	z-index: 16000;
	background: var(--fxr-surface-elevated, #fff);
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
	border-radius: var(--fxr-radius-md, 8px);
	box-shadow: var(--fxr-shadow-lg, 0 12px 32px rgba(15, 23, 42, 0.18));
}

.fvc-source-palette__search {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 10px;
	border-bottom: 1px solid var(--fxr-border-subtle, #e2e8f0);
	color: var(--fxr-text-muted, #64748b);
}

.fvc-source-palette__search input {
	flex: 1;
	min-width: 0;
	border: 0;
	outline: 0;
	background: transparent;
	color: var(--fxr-text-strong, #1e293b);
	font: inherit;
	font-size: 12px;
}

.fvc-source-palette__close {
	border: 0;
	padding: 2px 4px;
	background: transparent;
	color: inherit;
	cursor: pointer;
}

.fvc-source-palette :deep(.tg-mention-list) {
	min-width: 0;
	max-width: none;
	max-height: min(360px, 55vh);
	border: 0;
	border-radius: 0;
	box-shadow: none;
}
.fvc-empty-placeholder {
	position: absolute;
	top: 50%;
	transform: translateY(-50%);
	left: 0;
	color: var(--fxr-text-faint, #94a3b8);
	font-size: var(--fxr-input-font-size, 12px);
	pointer-events: none;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.fvc-main-field {
	display: flex;
	align-items: center;
	width: 100%;
	height: var(--fxr-input-height, 32px);
	min-height: var(--fxr-input-height, 32px);
	max-height: var(--fxr-input-height, 32px);
	overflow: hidden;
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-sm);
	background-color: var(--fxr-bg-input);
	transition: all 0.2s ease;
}

.fvc-main-field.is-multi-select {
	height: auto !important;
	min-height: var(--fxr-input-height, 32px) !important;
	max-height: none !important;
	overflow: visible !important;
}

.fvc-main-field:focus-within {
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-focus);
}

.fvc-static-container :deep(.combobox-wrapper),
.fvc-static-container :deep(.form-control),
.fvc-static-container :deep(.fxr-input),
.fvc-static-container :deep(.fxr-input-group),
.fvc-static-container :deep(.fxr-select),
.fvc-static-container :deep(.multi-select-trigger) {
	border: none !important;
	box-shadow: none !important;
	background: transparent !important;
	height: var(--fxr-input-height, 30px) !important;
	margin-bottom: 0 !important;
	padding-bottom: 0 !important;
	border-radius: inherit !important;
}

.fvc-static-container :deep(.fxr-control),
.fvc-static-container :deep(.fxr-input-group),
.fvc-static-container :deep(.combobox-container) {
	width: 100% !important;
	flex: 1 !important;
	min-width: 0 !important;
}

.fvc-static-container :deep(.fxr-input),
.fvc-static-container :deep(.fxr-select),
.fvc-static-container :deep(.combobox-input),
.fvc-static-container :deep(.awesomplete input) {
	padding: 0 10px !important;
	font-weight: var(--fxr-weight-bold) !important;
	color: var(--fxr-text-strong) !important;
	height: var(--fxr-input-height, 32px) !important;
}

.fvc-main-field:focus-within {
	border-color: var(--fxr-accent, #2490ef);
	box-shadow: 0 0 0 2px color-mix(in srgb, var(--fxr-accent, #2490ef) 20%, transparent);
	position: relative;
	z-index: 10;
}

.fvc-static-container {
	display: flex;
	align-items: center;
	flex: 1;
	height: 100%;
	min-width: 0;
	overflow: hidden;
}
.fvc-editor-container {
	padding: 2px 8px;
	flex: 1;
	position: relative;
	overflow: hidden;
}
.fvc-editor-wrapper {
	width: 100%;
	position: relative;
}
.fvc-source-browse-wrap,
.fvc-mode-toggle-wrap {
	padding-right: 4px;
	border-left: 1px solid var(--fxr-border-subtle);
	margin-left: 4px;
	height: 24px;
	display: flex;
	align-items: center;
	flex-shrink: 0;
}
.fvc-browse-btn,
.fvc-toggle-btn {
	background: transparent;
	border: none;
	cursor: pointer;
	color: var(--fxr-text-soft);
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 4px;
	transition: all 0.2s;
}
.fvc-browse-btn:hover,
.fvc-toggle-btn:hover {
	background-color: var(--fxr-bg-hover);
	color: var(--fxr-accent);
}

.fxr-picker-popover-backdrop {
	position: fixed;
	inset: 0;
	z-index: 14400;
	background: transparent;
}

.fvc-empty-hint {
	position: absolute;
	top: 50%;
	transform: translateY(-50%);
	left: 0;
	color: var(--fxr-text-faint);
	font-size: 11px;
	pointer-events: none;
	white-space: nowrap;
	font-family: var(--fxr-font-mono);
}
.fvc-empty-hint .hint-part {
	color: var(--fxr-text-soft);
	font-weight: 700;
}
.fvc-empty-hint .hint-at {
	color: #059669;
	font-weight: 700;
}
.fvc-empty-hint .hint-slash {
	color: #7c3aed;
	font-weight: 700;
}
.fvc-focus-hint {
	position: absolute;
	top: 50%;
	transform: translateY(-50%);
	left: 0;
	color: var(--fxr-text-faint);
	font-size: 12px;
	font-style: italic;
	pointer-events: none;
}
.fvc-tiptap-editor :deep(.ProseMirror) {
	outline: none;
	font-size: var(--fxr-input-font-size);
	min-height: 20px;
	display: flex;
	align-items: center;
	white-space: pre-wrap;
	overflow-x: auto;
	scrollbar-width: none;
}

.fvc-tiptap-editor :deep(.ProseMirror)::-webkit-scrollbar {
	display: none;
}

.fvc-inline-actions {
	position: absolute;
	right: 0;
	top: 50%;
	transform: translateY(-50%);
	display: flex;
	padding-right: 4px;
	background: linear-gradient(to left, var(--fxr-bg-input) 80%, transparent);
	z-index: 5;
}

.fvc-action-btn {
	background: transparent;
	border: none !important;
	outline: none !important;
	box-shadow: none !important;
	color: var(--fxr-text-muted);
	cursor: pointer;
	padding: 2px 4px;
	border-radius: 4px;
	font-size: 12px;
	transition: all 0.2s;
	display: flex;
	align-items: center;
	justify-content: center;
}

.fvc-action-btn:hover {
	color: var(--fxr-accent);
	background-color: var(--fxr-bg-hover);
}

:deep(.token-chip) {
	padding: 1px 6px;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 600;
	margin: 0 2px;
	cursor: pointer;
	display: inline-flex;
	align-items: center;
	transition: all 0.2s;
}
:deep(.token-chip:hover) {
	filter: brightness(0.95);
	transform: scale(1.02);
}
:deep(.token-variable) {
	background-color: var(--fxr-badge-bool);
	color: var(--fxr-badge-bool-text);
	border: 1px solid rgba(16, 185, 129, 0.2);
}
:deep(.token-formula) {
	background-color: var(--fxr-badge-var);
	color: var(--fxr-badge-var-text);
	border: 1px solid rgba(124, 58, 237, 0.2);
}
:deep(.token-normalize) {
	background-color: var(--fxr-badge-normalize);
	color: var(--fxr-badge-normalize-text);
	border: 1px solid rgba(37, 99, 235, 0.2);
}
:deep(.token-format) {
	background-color: var(--fxr-badge-formatter);
	color: var(--fxr-badge-formatter-text);
	border: 1px solid rgba(219, 39, 119, 0.2);
}
:deep(.token-resolver) {
	background-color: var(--fxr-badge-resolver);
	color: var(--fxr-badge-resolver-text);
	border: 1px solid rgba(217, 119, 6, 0.2);
}

.fxr-token-modal-overlay {
	position: fixed;
	inset: 0;
	background-color: rgba(0, 0, 0, 0.5);
	backdrop-filter: blur(8px);
	z-index: 13000;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 16px;
}
.fxr-token-modal-container {
	background-color: var(--fxr-surface-elevated);
	border-radius: 12px;
	width: 100%;
	max-width: 580px;
	overflow: hidden;
	box-shadow: var(--fxr-shadow-lg);
	border: 1px solid var(--fxr-border-subtle);
}
.fxr-token-modal-header {
	height: 52px;
	padding: 0 16px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	display: flex;
	justify-content: space-between;
	align-items: center;
}
.fxr-token-modal-body {
	padding: 16px;
	max-height: 70vh;
	overflow-y: auto;
}
.fxr-token-modal-footer {
	height: 56px;
	padding: 0 16px;
	border-top: 1px solid var(--fxr-border-subtle);
	display: flex;
	justify-content: flex-end;
	gap: 8px;
	background-color: var(--fxr-surface-2);
	align-items: center;
}

.formula-textarea {
	width: 100%;
	min-height: 120px;
	font-family: var(--fxr-font-mono);
	padding: 8px;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 6px;
	font-size: 13px;
	line-height: 1.5;
	background-color: var(--fxr-bg-input);
	color: var(--fxr-text);
}
.variables-pill-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	margin-top: 8px;
	max-height: 140px;
	overflow-y: auto;
	padding: 4px;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 6px;
	background-color: var(--fxr-surface-soft);
}
.var-pill-btn {
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-subtle);
	padding: 3px 8px;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 600;
	color: var(--fxr-text);
	cursor: pointer;
	transition: all 0.2s;
}
.var-pill-btn:hover {
	background-color: var(--fxr-bg-hover);
	border-color: var(--fxr-accent);
}
.json-textarea {
	width: 100%;
	min-height: 200px;
	font-family: monospace;
	font-size: 12px;
}

.fvc-wrap.has-error .fvc-main-field {
	border-color: var(--fxr-border-danger, var(--fxr-text-danger)) !important;
	box-shadow: 0 0 0 1px var(--fxr-border-danger, var(--fxr-text-danger)) !important;
}
.fvc-wrap.has-error .fvc-main-field:focus-within {
	border-color: var(--fxr-border-danger, var(--fxr-text-danger)) !important;
	box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.15) !important;
}
</style>
