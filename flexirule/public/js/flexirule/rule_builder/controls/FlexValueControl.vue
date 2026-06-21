<template>
	<div
		ref="controlRef"
		class="fvc-wrap"
		:class="{
			'is-compact': compact,
			'is-disabled': disabled || isReadOnly,
			'has-error': showValidation && !isValid,
		}"
		:data-fxr-fieldname="context?.df?.fieldname || fieldname || null"
		v-field-reveal="context?.df?.fieldname || fieldname || null"
		@keydown.capture="onStaticKeydown"
	>
		<!-- ── Main Control Area ── -->
		<div
			class="fvc-main-field"
			:class="{
				'is-dynamic': isDynamicMode || !isStaticSupported,
				'is-static-link': !isDynamicMode && isLinkType,
			}"
			@click="onWrapClick"
		>
			<!-- Static Mode (via ControlFactory or MultiSelectList) -->
			<div v-if="!isDynamicMode && isStaticSupported" class="fvc-static-container flex-1">
				<MultiSelectList
					v-if="isMultiSelect"
					:df="staticDf"
					:modelValue="staticValue"
					:documentType="isLinkType ? referenceDoctype : undefined"
					:options="isLinkType ? undefined : fieldOptions"
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

					<!-- Inline Actions (JSON Preview) -->
					<div class="fvc-inline-actions" v-if="!isReadOnly && !isEditorEmpty">
						<button
							class="fvc-action-btn"
							type="button"
							:title="__('JSON Preview')"
							@click.stop="openTokenEditor(null, null, 'json')"
						>
							<i class="fa fa-code"></i>
						</button>
					</div>

					<!-- Contextual placeholder -->
					<div
						v-if="!isReadOnly && isEditorEmpty && !isEditorFocused"
						class="fvc-empty-hint"
					>
						<span class="hint-part">|</span> {{ __("static") }}
						<span class="hint-sep">·</span>
						<span class="hint-at">@</span>{{ __("variable") }}
						<span class="hint-sep">·</span>
						<span class="hint-slash">/</span>{{ __("resolver") }}
					</div>
					<div
						v-else-if="!isReadOnly && isEditorEmpty && isEditorFocused"
						class="fvc-focus-hint"
					>
						{{
							placeholder ||
							__("Type Value or @ for Variable or / for advanced Resolver")
						}}
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

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", context?.df?.label || __("Field")) }}
		</div>

		<!-- ── Token Editor Modal ── -->
		<Teleport to="body">
			<div
				v-if="activeTokenType"
				class="fxr-token-modal-overlay"
				@click.self="closeTokenEditor"
			>
				<div class="fxr-token-modal-container">
					<!-- Header -->
					<div class="fxr-token-modal-header">
						<div class="d-flex align-items-center" style="gap: 8px">
							<i
								:class="activeTokenPresentation.icon"
								style="font-size: 14px; color: #64748b"
							></i>
							<span style="font-weight: 600; font-size: 14px">{{
								activeTokenPresentation.title
							}}</span>
						</div>
						<button
							type="button"
							class="fvc-action-btn"
							@click="closeTokenEditor"
							:title="__('Close')"
						>
							<i class="fa fa-times"></i>
						</button>
					</div>

					<!-- Body -->
					<div class="fxr-token-modal-body">
						<!-- JSON Editor Mode -->
						<template v-if="activeTokenType === 'json'">
							<textarea
								class="json-textarea"
								v-model="tokenDraftAttrs.value"
								:placeholder="__('Paste or edit JSON/Expression here...')"
							></textarea>
							<div
								v-if="jsonParseError"
								class="text-danger mt-1"
								style="font-size: 12px"
							>
								{{ jsonParseError }}
							</div>
						</template>

						<!-- Visual Builder / Manual Editor -->
						<template v-else>
							<!-- Mode Toggle: Builder vs Manual -->
							<div class="d-flex align-items-center justify-content-between mb-3">
								<span class="fxr-label-sm mb-0">{{ __("Edit Mode") }}</span>
								<div class="d-flex align-items-center" style="gap: 6px">
									<button
										type="button"
										class="fvc-action-btn"
										:style="
											!isManualMode
												? 'color: var(--fxr-accent); font-weight: 700'
												: ''
										"
										@click="isManualMode = false"
									>
										<i class="fa fa-th-large mr-1"></i> {{ __("Visual") }}
									</button>
									<span style="color: #cbd5e1">|</span>
									<button
										type="button"
										class="fvc-action-btn"
										:style="
											isManualMode
												? 'color: var(--fxr-accent); font-weight: 700'
												: ''
										"
										@click="isManualMode = true"
									>
										<i class="fa fa-code mr-1"></i> {{ __("Manual") }}
									</button>
								</div>
							</div>

							<!-- Visual Builder -->
							<div v-if="!isManualMode">
								<ValueResolverControl
									viewMode="inline"
									:modelValue="tokenDraftAttrs.config"
									:doctype="triggerDoctype"
									:context="resolverContext"
									:variableOptions="availableVariableOptions"
									:allowedKinds="allowedBuilderKinds"
									@update:modelValue="handleBuilderUpdate"
								/>
								<div v-if="builderErrors.length" class="mt-3">
									<div
										v-for="err in builderErrors"
										:key="err"
										class="text-danger fxr-text-xs"
									>
										<i class="fa fa-exclamation-triangle mr-1"></i> {{ err }}
									</div>
								</div>
							</div>

							<!-- Manual Formula Editor -->
							<div v-else>
								<div class="d-flex flex-column" style="gap: 8px">
									<label class="fxr-label-sm">{{ __("Expression") }}</label>
									<textarea
										ref="formulaTextareaRef"
										class="formula-textarea"
										v-model="tokenDraftAttrs.expression"
										:placeholder="
											__('e.g. frappe.utils.add_days(doc.posting_date, 7)')
										"
									></textarea>
								</div>

								<!-- Variable pills -->
								<div
									v-if="
										availableVariableOptions && availableVariableOptions.length
									"
									class="mt-2"
								>
									<label class="fxr-label-sm">{{ __("Insert Variable") }}</label>
									<div class="variables-pill-grid">
										<button
											v-for="v in availableVariableOptions"
											:key="v.value || v"
											type="button"
											class="var-pill-btn"
											@click="insertVarInFormula(v)"
										>
											{{ v.label || v }}
										</button>
									</div>
								</div>

								<!-- Config params for resolver -->
								<div class="mt-3" v-if="activeTokenType === 'resolver'">
									<div
										class="d-flex align-items-center justify-content-between mb-2"
									>
										<label class="fxr-label-sm mb-0">{{ __("Config") }}</label>
										<button
											type="button"
											class="fvc-action-btn"
											@click="addConfigParam"
										>
											<i class="fa fa-plus mr-1"></i> {{ __("Add Param") }}
										</button>
									</div>
									<div
										v-if="
											tokenDraftAttrs.config &&
											typeof tokenDraftAttrs.config === 'object'
										"
										class="d-flex flex-column"
										style="gap: 6px"
									>
										<div
											v-for="(val, key) in tokenDraftAttrs.config"
											:key="key"
											class="d-flex align-items-center"
											style="gap: 6px"
										>
											<input
												type="text"
												class="fxr-input"
												style="width: 120px; font-size: 12px"
												:value="key"
												@change="renameConfigKey(key, $event.target.value)"
												:placeholder="__('key')"
											/>
											<input
												type="text"
												class="fxr-input flex-1"
												style="font-size: 12px"
												v-model="tokenDraftAttrs.config[key]"
												:placeholder="__('value')"
											/>
											<button
												type="button"
												class="fvc-action-btn"
												@click="removeConfigKey(key)"
											>
												<i class="fa fa-trash"></i>
											</button>
										</div>
									</div>
								</div>
							</div>
						</template>
					</div>

					<!-- Footer -->
					<div class="fxr-token-modal-footer">
						<button
							type="button"
							class="fxr-btn fxr-btn--secondary"
							@click="closeTokenEditor"
						>
							{{ __("Cancel") }}
						</button>
						<button
							type="button"
							class="fxr-btn fxr-btn--primary"
							@click="saveTokenEditor"
							:disabled="!isManualMode && !isBuilderValid"
						>
							{{ __("Save") }}
						</button>
					</div>
				</div>
			</div>
		</Teleport>
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
} from "../../core/formula_registry";
import { compileToCode, compileToLabel } from "../../core/builder_utils.js";
import MentionList from "./MentionList.vue";
import ControlFactory from "./ControlFactory.vue";
import MultiSelectList from "./MultiSelectList.vue";
import ValueResolverControl from "./ValueResolverControl.vue";
import ResolverTokenView from "./ResolverTokenView.vue";

const props = defineProps({
	modelValue: { type: [Object, String, Number, Boolean], default: null },
	fieldname: String,
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
	compact: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	engine: { type: Object, default: null },
	doc: { type: Object, default: null },
	showValidation: { type: Boolean, default: false },
	/**
	 * Structured context:
	 * {
	 *   df: { fieldtype, options, fieldname, ... },
	 *   operator: 'set',
	 *   referenceDoctype: 'Customer', // fallback if not in df
	 *   onUpdate: Function // optional callback
	 * }
	 */
	context: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:modelValue", "update"]);

const isReadOnly = computed(() => !!props.readOnly || !!props.read_only);
const isMultiSelect = computed(() => {
	const op = props.context?.operator;
	const isListOp = op === "in list" || op === "not in list";
	if (!isListOp) return false;

	const ft = fieldType.value;
	return (
		ft === "Select" || PURE_TEXT_FIELDTYPES.has(ft) || ft === "Link" || ft === "Dynamic Link"
	);
});
const isDynamicMode = ref(false);
const isEditorFocused = ref(false);
const isSuggestionOpen = ref(false);
const activeTippyPopups = [];
const uid =
	Math.random().toString(36).substring(2, 15) + "_" + Math.random().toString(36).substring(2, 15);

const controlRef = ref(null);
const formulaTextareaRef = ref(null);

// Modal state
const activeTokenType = ref(null);
const activeTokenNode = ref(null);
const activeTokenPos = ref(null);
const tokenDraftAttrs = ref({});
const jsonParseError = ref("");
const isBuilderValid = ref(true);
const builderErrors = ref([]);

// Static Mode Helpers
const staticValue = ref("");

const fieldType = computed(() => props.context?.df?.fieldtype || "Data");
const fieldOptions = computed(() => props.context?.df?.options || []);
const referenceDoctype = computed(() => {
	if (fieldType.value === "Link" && fieldOptions.value) {
		return fieldOptions.value;
	}
	return props.context?.referenceDoctype || fieldOptions.value || "";
});

const triggerDoctype = computed(() => {
	return props.doctype || props.engine?.rule_doc?.document_type || "";
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

const isLinkType = computed(() => fieldType.value === "Link" || fieldType.value === "Dynamic Link");

const PURE_TEXT_FIELDTYPES = new Set([
	"Data",
	"Small Text",
	"Text",
	"Long Text",
	"Code",
	"Text Editor",
	"JSON",
]);

const isStaticSupported = computed(() => {
	if (isMultiSelect.value) return true;
	return !PURE_TEXT_FIELDTYPES.has(fieldType.value);
});

const RESOLVER_LEVEL_KIND_MAP = {
	basic: ["system_context", "string_formula", "normalization", "format"],
	standard: [
		"date_formula",
		"date_diff",
		"system_context",
		"string_formula",
		"normalization",
		"format",
	],
	advanced: [
		"date_formula",
		"date_diff",
		"math_formula",
		"child_aggregation",
		"system_context",
		"string_formula",
		"normalization",
		"format",
	],
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
	let ft = fieldType.value;
	let opts = fieldOptions.value;

	if (ft === "Link") {
		opts = referenceDoctype.value;
	}

	return {
		...props.context?.df,
		fieldtype: ft,
		label: "",
		options: opts,
		read_only: props.disabled || isReadOnly.value,
		placeholder: props.placeholder,
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
			config: { default: null },
			resolver: { default: "" }, // legacy compat
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
		const kind = node.attrs.config?.kind || "resolver";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "resolver",
				"data-config": JSON.stringify(node.attrs.config),
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
			// Destroy any existing popups to prevent duplicates
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
				} catch (e) {
					// Ignore error during popup destruction
				}
				const idx = activeTippyPopups.indexOf(popup);
				if (idx > -1) activeTippyPopups.splice(idx, 1);
				popup = null;
			}
			if (component) {
				try {
					component.destroy();
				} catch (e) {
					// Ignore error during component destruction
				}
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
			doctype: referenceDoctype.value,
			readOnly: isReadOnly.value,
			context: resolverContext.value,
		}),
		VariableTrigger.configure({
			suggestion: {
				char: "@",
				pluginKey: new PluginKey(`variableTrigger_${uid}`),
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					const base = [
						{ id: "doc", label: "doc", type: "variable", icon: "📄" },
						{ id: "vars", label: "vars", type: "variable", icon: "📦" },
					];
					const options = [
						...base,
						...availableVariableOptions.value.map((v) => ({
							id: v.value || v,
							label: v.label || v,
							type: "variable",
							icon: "fa fa-cube",
						})),
					];
					return options
						.filter(
							(v) =>
								v.id.toLowerCase().includes(q) || v.label.toLowerCase().includes(q)
						)
						.slice(0, 20);
				},
				command: ({ editor, range, props }) => {
					editor
						.chain()
						.focus()
						.insertContentAt(range, [
							{
								type: "variableToken",
								attrs: { path: props.id, label: props.label },
							},
						])
						.run();
				},
			},
		}),
		CommandTrigger.configure({
			suggestion: {
				char: "/",
				pluginKey: new PluginKey(`commandTrigger_${uid}`),
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					let commands = getCommandsForFieldtype(fieldType.value);
					let formulas = getFormulasForFieldtype(fieldType.value);

					if (typeof props.context?.filterCommands === "function") {
						commands = commands.filter((cmd) =>
							props.context.filterCommands(cmd, {
								fieldType: fieldType.value,
								context: props.context,
							})
						);
					}
					if (typeof props.context?.filterFormulas === "function") {
						formulas = formulas.filter((formula) =>
							props.context.filterFormulas(formula, {
								fieldType: fieldType.value,
								context: props.context,
							})
						);
					}

					const mappedFormulas = formulas.map((f) => ({
						id: f.id,
						label: f.label,
						type: "logic",
						icon: "fa fa-calculator",
						description: f.description,
					}));

					return [...commands, ...mappedFormulas].filter((c) =>
						c.label.toLowerCase().includes(q)
					);
				},
				command: ({ editor, range, props }) => {
					if (props.id === "clear") {
						editor.chain().focus().setContent("").run();
						return;
					}

					const commands = getCommandsForFieldtype(fieldType.value);
					const isCommand = commands.find((c) => c.id === props.id);

					if (isCommand) {
						const preferredKindMap = {
							formula: "math_formula",
							normalize: "normalization",
							formatter: "format",
							resolver: "string_formula",
							fetch: "fetch",
						};
						const allowedKinds = Array.isArray(allowedBuilderKinds.value)
							? allowedBuilderKinds.value
							: [];
						let initialKind = preferredKindMap[props.id] || "string_formula";
						if (allowedKinds.length && !allowedKinds.includes(initialKind)) {
							initialKind = allowedKinds[0];
						}

						editor
							.chain()
							.focus()
							.insertContentAt(range, [
								{
									type: "resolverToken",
									attrs: { config: { kind: initialKind } },
								},
							])
							.run();
					} else {
						editor.chain().focus().insertContentAt(range, `${props.label}()`).run();
					}
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
		return struct.value !== undefined && struct.value !== null && struct.value !== "";
	}
	if (struct.mode === "variable") return !!struct.value;
	if (struct.mode === "resolver") return !!struct.value;
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
	if (val && typeof val === "object" && val.mode) {
		// Legacy specialized modes are collapsed to resolver mode.
		if (["formula", "format", "normalize", "normalization"].includes(val.mode)) {
			const config = { ...(val.config || {}) };
			if (!config.kind) {
				if (val.mode === "formula") config.kind = "math_formula";
				if (val.mode === "format") config.kind = "format";
				if (val.mode === "normalize" || val.mode === "normalization") {
					config.kind = "normalization";
				}
			}
			return {
				mode: "resolver",
				value: val.value || val.expression || val.resolver || compileToCode(config) || "",
				config,
			};
		}
		if (val.mode === "variable") {
			return { mode: "variable", value: val.value || val.path || "" };
		}
		if (val.mode === "resolver") {
			const config = val.config || null;
			const expr = val.value || val.expression || val.resolver || "";
			return config
				? { mode: "resolver", value: expr, config }
				: { mode: "resolver", value: expr };
		}
		if (val.mode === "expression") {
			return { mode: "expression", value: Array.isArray(val.value) ? val.value : [] };
		}
		return { mode: "static", value: val.value };
	}

	if (val === null || val === undefined) {
		return { mode: "static", value: "" };
	}
	return { mode: "static", value: val };
}

function serialize() {
	if (editor.isEmpty && !isDynamicMode.value) {
		return { mode: "static", value: staticValue.value };
	}

	const doc = editor.getJSON();
	const content = doc.content?.[0]?.content || [];

	if (content.length === 0) return { mode: "static", value: "" };

	// If there's exactly one token and nothing else, use its mode
	if (content.length === 1 && content[0].type !== "text") {
		const node = content[0];
		const typeName = node.type.name || node.type;
		if (typeName === "variableToken") {
			return {
				mode: "variable",
				value: node.attrs.path,
			};
		}
		if (typeName === "resolverToken") {
			const config = node.attrs.config || null;
			const expression =
				node.attrs.expression || node.attrs.resolver || compileToCode(config || {}) || "";
			return {
				mode: "resolver",
				value: expression,
				...(config ? { config } : {}),
			};
		}
	}

	// Mixed content or multiple tokens -> expression mode
	const tokens = content.map((item) => {
		if (item.type === "text") return { type: "text", value: item.text };

		// For mixed mode, the expression MUST be wrapped in {} if it was a builder code
		let expr = item.attrs.expression || item.attrs.path || "";
		if (item.type === "variableToken") expr = `{${expr}}`;
		// if expression already has {}, it's likely correct.
		// Builder output from compileToCode already includes {}.

		return { type: item.type, attrs: { ...item.attrs, expression: expr } };
	});

	return { mode: "expression", value: tokens };
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

	if (structured.mode === "variable")
		return `<span data-token-type="variable" data-path="${escapeAttr(
			structured.value
		)}" data-label=""></span>`;

	if (structured.mode === "resolver") {
		return `<span data-token-type="resolver" data-expression="${escapeAttr(
			structured.value
		)}" data-label="" data-config='${escapeAttr(
			JSON.stringify(structured.config || null)
		)}'></span>`;
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
	if (json === lastEmittedJSON) return; // idempotency guard: prevent feedback loops
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
	if (isDynamicMode.value || !isStaticSupported.value) editor.commands.focus();
}

function toggleDynamicMode() {
	if (isReadOnly.value || props.disabled) return;
	if (isDynamicMode.value) {
		// Switching TO static: only allow if editor content is pure text
		const struct = serialize();
		if (struct.mode === "static") {
			isDynamicMode.value = false;
			staticValue.value = struct.value ?? "";
			emitChanges();
		}
		// If variable/resolver in editor → refuse to switch, value stays safe
	} else {
		// Switching TO dynamic
		isDynamicMode.value = true;
		const prev = staticValue.value;
		lastEmittedJSON = ""; // force re-emit after content change
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
		lastEmittedJSON = ""; // allow next emitChanges to propagate
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
		lastEmittedJSON = ""; // allow next emitChanges to propagate
		nextTick(() => {
			editor.commands.setContent("");
			editor.commands.insertContent({
				type: "variableToken",
				attrs: { path, label: path },
			});
			// editor.onUpdate → emitChanges() handles the rest
		});
		return;
	}
	staticValue.value = val;
	emitChanges();
}

// ── Token Editor ──

const isManualMode = ref(false);

const activeTokenPresentation = computed(() => {
	const map = {
		formula: { title: __("Configure Formula"), icon: "fa fa-calculator" },
		resolver: { title: __("Configure Resolver"), icon: "fa fa-bolt" },
		normalize: { title: __("Configure Normalization"), icon: "fa fa-refresh" },
		format: { title: __("Configure Format"), icon: "fa fa-paint-brush" },
		fetch: { title: __("Fetch From Link"), icon: "fa fa-link" },
		json: { title: __("JSON Editor"), icon: "fa fa-code" },
	};
	return map[activeTokenType.value] || { title: __("Token Configuration"), icon: "fa fa-cog" };
});

function openTokenEditor(node, pos, typeOverride = null) {
	if (isReadOnly.value) return;
	activeTokenNode.value = node;
	activeTokenPos.value = pos;
	isManualMode.value = false;

	if (typeOverride) {
		activeTokenType.value = typeOverride;
		tokenDraftAttrs.value = { value: editor.getText() };
		return;
	}

	if (node.type.name === "resolverToken") {
		const kind = node.attrs.config?.kind;
		if (["normalization", "format", "fetch"].includes(kind)) {
			if (kind === "normalization") activeTokenType.value = "normalize";
			else if (kind === "format") activeTokenType.value = "format";
			else activeTokenType.value = "fetch";
		} else if (kind?.includes("formula") || kind?.includes("aggregation")) {
			activeTokenType.value = "formula";
		} else {
			activeTokenType.value = "resolver";
		}

		tokenDraftAttrs.value = {
			expression: node.attrs.expression,
			resolver: node.attrs.resolver,
			label: node.attrs.label,
			config: node.attrs.config || null,
		};
	}

	if (activeTokenType.value && !tokenDraftAttrs.value.config) {
		isManualMode.value = true;
	}
}

function closeTokenEditor() {
	activeTokenType.value = null;
	tokenDraftAttrs.value = {};
	builderErrors.value = [];
	isBuilderValid.value = true;
}

function handleBuilderUpdate(config, details) {
	const defaults =
		typeof props.context?.resolverDefaults === "function"
			? props.context.resolverDefaults({
					fieldType: fieldType.value,
					referenceDoctype: referenceDoctype.value,
					context: props.context,
				})
			: props.context?.resolverDefaults;
	const mergedConfig =
		defaults && typeof defaults === "object" ? { ...defaults, ...config } : config;
	tokenDraftAttrs.value.config = mergedConfig;
	tokenDraftAttrs.value.expression = details?.expression || compileToCode(mergedConfig);
	tokenDraftAttrs.value.label = details?.label || compileToLabel(mergedConfig);
	isBuilderValid.value = details?.isValid ?? true;
	builderErrors.value = details?.errors || [];
}

function saveTokenEditor() {
	lastEmittedJSON = ""; // force re-emit after editor content change
	if (activeTokenType.value === "json") {
		editor.commands.setContent(tokenDraftAttrs.value.value);
		emitChanges();
	} else {
		if (isManualMode.value) {
			tokenDraftAttrs.value.config = null;
		}

		editor
			.chain()
			.focus()
			.setNodeSelection(activeTokenPos.value)
			.updateAttributes(activeTokenNode.value.type.name, tokenDraftAttrs.value)
			.run();
		emitChanges();
	}
	closeTokenEditor();
}

function insertVarInFormula(v) {
	const textarea = formulaTextareaRef.value;
	const start = textarea.selectionStart;
	const insert = v.value || v;
	tokenDraftAttrs.value.expression =
		textarea.value.slice(0, start) + insert + textarea.value.slice(textarea.selectionEnd);
}

function addConfigParam() {
	if (!tokenDraftAttrs.value.config) tokenDraftAttrs.value.config = {};
	const key = `param_${Object.keys(tokenDraftAttrs.value.config).length + 1}`;
	tokenDraftAttrs.value.config[key] = "";
}

function removeConfigKey(key) {
	delete tokenDraftAttrs.value.config[key];
}

function renameConfigKey(oldKey, newKey) {
	if (!newKey || oldKey === newKey) return;
	const val = tokenDraftAttrs.value.config[oldKey];
	delete tokenDraftAttrs.value.config[oldKey];
	tokenDraftAttrs.value.config[newKey] = val;
}

watch(
	() => props.modelValue,
	(val) => {
		const normalized = coerceStructuredValue(val);
		const json = JSON.stringify(normalized);
		if (json === lastEmittedJSON) return; // our own emission, skip
		if (normalized.mode !== "static") {
			isDynamicMode.value = true;
			editor.commands.setContent(deserialize(normalized));
			lastEmittedJSON = json; // prevent editor.onUpdate from re-emitting
		} else {
			isDynamicMode.value = false;
			staticValue.value = normalized.value ?? "";
		}
	},
	{ immediate: true }
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

.fvc-main-field:focus-within {
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-focus);
}

/* Deep override to remove internal borders from nested controls in static mode */
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
.fvc-mode-toggle-wrap {
	padding-right: 6px;
	border-left: 1px solid var(--fxr-border-subtle);
	margin-left: 4px;
	height: 24px;
	display: flex;
	align-items: center;
	flex-shrink: 0;
}
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
.fvc-toggle-btn:hover {
	background-color: var(--fxr-bg-hover);
	color: var(--fxr-accent);
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
	white-space: nowrap;
	overflow-x: auto;
	scrollbar-width: none; /* Firefox */
}

.fvc-tiptap-editor :deep(.ProseMirror)::-webkit-scrollbar {
	display: none; /* Safari and Chrome */
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
</style>
