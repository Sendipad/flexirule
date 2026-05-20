<template>
	<div
		ref="controlRef"
		class="fvc-wrap"
		:class="{ 'is-compact': compact, 'is-disabled': disabled || isReadOnly }"
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
			<!-- Static Mode (via ControlFactory) -->
			<div v-if="!isDynamicMode && isStaticSupported" class="fvc-static-container flex-1">
				<ControlFactory
					:df="staticDf"
					:modelValue="staticValue"
					:doc="doc"
					:engine="engine"
					:options="isLinkType ? undefined : options"
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
						<span class="hint-slash">/</span>{{ __("command") }}
					</div>
					<div
						v-else-if="!isReadOnly && isEditorEmpty && isEditorFocused"
						class="fvc-focus-hint"
					>
						{{ placeholder || __("Type value, @variable or /command...") }}
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

		<!-- ── Token Editor Modals (Teleported) ── -->
		<Teleport to="body">
			<div
				v-if="activeTokenType"
				class="fxr-token-modal-overlay"
				@click.self="closeTokenEditor"
			>
				<div
					class="fxr-token-modal-container"
					:class="{
						'full-expanded':
							activeTokenType === 'condition' || activeTokenType === 'normalize',
					}"
				>
					<div class="fxr-token-modal-header">
						<span class="header-title">
							<i
								:class="activeTokenPresentation.icon"
								class="me-2 text-primary fw-medium"
							></i>
							{{ activeTokenPresentation.title }}
						</span>
						<button class="btn-close" @click="closeTokenEditor">
							<i class="fa fa-times"></i>
						</button>
					</div>
					<div class="fxr-token-modal-body">
						<!-- Builder Toggle -->
						<div
							v-if="activeTokenType && activeTokenType !== 'json'"
							class="builder-mode-toggle mb-3 d-flex justify-content-end"
						>
							<div class="fxr-btn-group">
								<button
									class="fxr-btn fxr-btn--xs"
									:class="!isManualMode ? 'fxr-btn--primary' : 'fxr-btn--ghost'"
									@click="isManualMode = false"
								>
									{{ __("Builder") }}
								</button>
								<button
									class="fxr-btn fxr-btn--xs"
									:class="isManualMode ? 'fxr-btn--primary' : 'fxr-btn--ghost'"
									@click="isManualMode = true"
								>
									{{ __("Manual") }}
								</button>
							</div>
						</div>

						<template v-if="!isManualMode && activeTokenType === 'formula'">
							<ValueResolverControl
								viewMode="inline"
								:modelValue="tokenDraftAttrs.config"
								:doctype="referenceDoctype"
								:allowedKinds="['date_formula', 'math_formula', 'date_diff']"
								@update:modelValue="handleBuilderUpdate"
							/>
						</template>

						<template v-else-if="!isManualMode && activeTokenType === 'normalize'">
							<ValueResolverControl
								viewMode="inline"
								:modelValue="tokenDraftAttrs.config"
								:doctype="referenceDoctype"
								:allowedKinds="['normalization']"
								@update:modelValue="handleBuilderUpdate"
							/>
						</template>

						<template v-else-if="!isManualMode && activeTokenType === 'format'">
							<ValueResolverControl
								viewMode="inline"
								:modelValue="tokenDraftAttrs.config"
								:doctype="referenceDoctype"
								:allowedKinds="['format']"
								@update:modelValue="handleBuilderUpdate"
							/>
						</template>

						<template v-else-if="!isManualMode && activeTokenType === 'resolver'">
							<div class="d-flex flex-column fxr-gap-3">
								<div class="d-flex flex-column fxr-gap-1">
									<label class="fxr-label-sm">{{
										__("Value Resolver Type")
									}}</label>
									<select class="fxr-select" v-model="tokenDraftAttrs.resolver">
										<option value="query_record">
											{{ __("Query Record") }}
										</option>
										<option value="resolve_user">
											{{ __("Resolve Current User") }}
										</option>
										<option value="fetch_global_setting">
											{{ __("Fetch Global Setting") }}
										</option>
										<option value="custom">
											{{ __("Custom API/Method") }}
										</option>
									</select>
								</div>
								<div class="d-flex flex-column fxr-gap-1 mt-2">
									<label class="fxr-label-sm d-flex justify-content-between">
										<span>{{ __("Parameters Config") }}</span>
										<button
											class="fxr-btn fxr-btn--sm fxr-btn--secondary py-0"
											@click="addConfigParam"
										>
											<i class="fa fa-plus me-1"></i> {{ __("Add Param") }}
										</button>
									</label>
									<div class="params-editor-list">
										<div
											v-for="(v, k) in tokenDraftAttrs.config"
											:key="k"
											class="param-row d-flex fxr-gap-2 align-items-center mb-2"
										>
											<input
												class="fxr-input flex-1"
												:value="k"
												@change="renameConfigKey(k, $event.target.value)"
												placeholder="Key"
											/>
											<input
												class="fxr-input flex-2"
												v-model="tokenDraftAttrs.config[k]"
												placeholder="Value"
											/>
											<button
												class="fxr-btn fxr-btn--icon fxr-btn--sm fxr-btn--ghost text-danger px-0"
												@click="removeConfigKey(k)"
											>
												<i class="fa fa-trash"></i>
											</button>
										</div>
									</div>
								</div>
							</div>
						</template>

						<template v-if="isManualMode && activeTokenType !== 'resolver'">
							<div class="d-flex flex-column fxr-gap-2">
								<label class="fxr-label-sm">{{ __("Manual Expression") }}</label>
								<textarea
									ref="formulaTextareaRef"
									class="fxr-textarea formula-textarea"
									v-model="tokenDraftAttrs.expression"
								></textarea>
								<div class="variables-selector-pane mt-3">
									<label class="fxr-label-sm">{{ __("Insert Variable") }}</label>
									<div class="variables-pill-grid v2-scrollbar">
										<button
											v-for="v in variableOptions"
											:key="v.value || v"
											class="var-pill-btn"
											@click="insertVarInFormula(v)"
										>
											{{ v.label || v.value || v }}
										</button>
									</div>
								</div>
							</div>
						</template>

						<template v-if="activeTokenType === 'json'">
							<div class="d-flex flex-column fxr-gap-3">
								<label class="fxr-label-sm">{{ __("JSON Data Editor") }}</label>
								<textarea
									class="fxr-textarea json-textarea"
									v-model="tokenDraftAttrs.value"
									placeholder='{ "key": "value" }'
								></textarea>
								<div v-if="jsonParseError" class="text-danger fxr-text-xs">
									{{ jsonParseError }}
								</div>
							</div>
						</template>
					</div>
					<footer class="fxr-token-modal-footer">
						<button
							class="fxr-btn fxr-btn--sm fxr-btn--secondary"
							@click="closeTokenEditor"
						>
							{{ __("Cancel") }}
						</button>
						<button
							class="fxr-btn fxr-btn--sm fxr-btn--primary"
							@click="saveTokenEditor"
						>
							{{ __("Save") }}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount, nextTick } from "vue";
import { Editor, EditorContent, VueRenderer } from "@tiptap/vue-3";
import { StarterKit } from "@tiptap/starter-kit";
import { Node, mergeAttributes } from "@tiptap/core";
import Mention from "@tiptap/extension-mention";
import { PluginKey } from "@tiptap/pm/state";
import tippy from "tippy.js";

import { getCommandsForFieldtype, getFormulasForFieldtype } from "../../core/formula_registry";
import { compileToCode, compileToLabel } from "../../core/builder_utils.js";
import MentionList from "./MentionList.vue";
import ControlFactory from "./ControlFactory.vue";
import ValueResolverControl from "./ValueResolverControl.vue";

const props = defineProps({
	modelValue: { type: [Object, String, Number, Boolean], default: null },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
	fieldType: { type: String, default: "Data" },
	compact: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	options: { type: [Array, String], default: () => [] },
	engine: { type: Object, default: null },
	doc: { type: Object, default: null },
	operator: { type: String, default: "" },
	referenceDoctype: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "update"]);

const isReadOnly = computed(() => !!props.readOnly || !!props.read_only);
const isDynamicMode = ref(false);
const isEditorFocused = ref(false);
const isSuggestionOpen = ref(false);

const controlRef = ref(null);
const formulaTextareaRef = ref(null);

// Modal state
const activeTokenType = ref(null);
const activeTokenNode = ref(null);
const activeTokenPos = ref(null);
const tokenDraftAttrs = ref({});
const jsonParseError = ref("");

// Static Mode Helpers
const staticValue = ref("");

const isLinkType = computed(() => props.fieldType === "Link" || props.fieldType === "Dynamic Link");

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
	return !PURE_TEXT_FIELDTYPES.has(props.fieldType);
});

const staticDf = computed(() => {
	let ft = props.fieldType;
	let opts = props.options;

	if (ft === "Link") {
		opts = props.referenceDoctype;
	}

	return {
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
		return { path: { default: "" }, label: { default: "" } };
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

const FormulaToken = Node.create({
	name: "formulaToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			expression: { default: "" },
			label: { default: "" },
			config: { default: null },
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="formula"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.label || node.attrs.expression || "Formula";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "formula",
				class: "token-chip token-formula",
			}),
			`🧮 ${label}`,
		];
	},
});

const ResolverToken = Node.create({
	name: "resolverToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			resolver: { default: "" },
			label: { default: "" },
			config: { default: null },
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="resolver"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.label || node.attrs.resolver || "Resolve";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "resolver",
				class: "token-chip token-resolver",
			}),
			`⚡ ${label}`,
		];
	},
});

const NormalizeToken = Node.create({
	name: "normalizeToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			expression: { default: "" },
			label: { default: "" },
			config: { default: null },
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="normalize"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.label || node.attrs.expression || "Normalize";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "normalize",
				class: "token-chip token-normalize",
			}),
			`🔄 ${label}`,
		];
	},
});

const FormatToken = Node.create({
	name: "formatToken",
	group: "inline",
	inline: true,
	selectable: true,
	atom: true,
	addAttributes() {
		return {
			expression: { default: "" },
			label: { default: "" },
			config: { default: null },
		};
	},
	parseHTML() {
		return [{ tag: 'span[data-token-type="format"]' }];
	},
	renderHTML({ node, HTMLAttributes }) {
		const label = node.attrs.label || node.attrs.expression || "Format";
		return [
			"span",
			mergeAttributes(HTMLAttributes, {
				"data-token-type": "format",
				class: "token-chip token-format",
			}),
			`🎨 ${label}`,
		];
	},
});

const VariableTrigger = Mention.extend({ name: "variableTrigger" });
const CommandTrigger = Mention.extend({ name: "commandTrigger" });

function createSuggestionRenderer() {
	let component;
	let popup;
	return {
		onStart: (props) => {
			isSuggestionOpen.value = true;
			component = new VueRenderer(MentionList, { props, editor: props.editor });
			popup = tippy("body", {
				getReferenceClientRect: props.clientRect,
				appendTo: () => document.body,
				content: component.element,
				showOnCreate: true,
				interactive: true,
				trigger: "manual",
				placement: "bottom-start",
			});
		},
		onUpdate(props) {
			component?.updateProps(props);
			popup?.[0]?.setProps({ getReferenceClientRect: props.clientRect });
		},
		onKeyDown(props) {
			if (props.event.key === "Escape") {
				popup?.[0]?.hide();
				return true;
			}
			return component?.ref?.onKeyDown(props);
		},
		onExit() {
			isSuggestionOpen.value = false;
			popup?.[0]?.destroy();
			component?.destroy();
		},
	};
}

let emitting = false;

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
		FormulaToken,
		ResolverToken,
		NormalizeToken,
		FormatToken,
		VariableTrigger.configure({
			suggestion: {
				char: "@",
				pluginKey: new PluginKey("variableTrigger"),
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					const base = [
						{ id: "doc", label: "doc", type: "variable", icon: "📄" },
						{ id: "vars", label: "vars", type: "variable", icon: "📦" },
					];
					const options = [
						...base,
						...(props.variableOptions || []).map((v) => ({
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
				pluginKey: new PluginKey("commandTrigger"),
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					const commands = getCommandsForFieldtype(props.fieldType);
					const formulas = getFormulasForFieldtype(props.fieldType);

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

					const commands = getCommandsForFieldtype(props.fieldType);
					const isCommand = commands.find((c) => c.id === props.id);

					if (isCommand) {
						const typeMap = {
							formula: "formulaToken",
							resolver: "resolverToken",
							normalize: "normalizeToken",
							formatter: "formatToken",
						};
						const nodeType = typeMap[props.id] || "formulaToken";
						editor
							.chain()
							.focus()
							.insertContentAt(range, [{ type: nodeType, attrs: {} }])
							.run();
						nextTick(() => {
							const { selection } = editor.state;
							const node = editor.state.doc.nodeAt(selection.$from.pos - 1);
							if (node) openTokenEditor(node, selection.$from.pos - 1);
						});
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
		if (!emitting) emitChanges();
	},
	onFocus: () => {
		isEditorFocused.value = true;
	},
	onBlur: () => {
		isEditorFocused.value = false;
	},
});

const isEditorEmpty = computed(() => editor.isEmpty);

// ── Serialization ──

function serialize() {
	if (editor.isEmpty && !isDynamicMode.value) {
		return { mode: "static", value: staticValue.value, fieldtype: props.fieldType };
	}

	const doc = editor.getJSON();
	const content = doc.content?.[0]?.content || [];

	if (content.length === 0) return { mode: "static", value: "", fieldtype: props.fieldType };

	// If there's exactly one token and nothing else, use its mode
	if (content.length === 1 && content[0].type !== "text") {
		const node = content[0];
		if (node.type === "variableToken") {
			return {
				mode: "variable",
				value: node.attrs.path,
				label: node.attrs.label,
				fieldtype: props.fieldType,
			};
		}
		if (node.type === "formulaToken") {
			return {
				mode: "formula",
				value: node.attrs.expression,
				label: node.attrs.label,
				config: node.attrs.config,
				fieldtype: props.fieldType,
			};
		}
		if (node.type === "resolverToken") {
			return {
				mode: "resolver",
				value: node.attrs.resolver,
				label: node.attrs.label,
				config: node.attrs.config,
				fieldtype: props.fieldType,
			};
		}
		if (node.type === "normalizeToken") {
			return {
				mode: "normalize",
				value: node.attrs.expression,
				label: node.attrs.label,
				config: node.attrs.config,
				fieldtype: props.fieldType,
			};
		}
		if (node.type === "formatToken") {
			return {
				mode: "format",
				value: node.attrs.expression,
				label: node.attrs.label,
				config: node.attrs.config,
				fieldtype: props.fieldType,
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

	return { mode: "expression", value: tokens, fieldtype: props.fieldType };
}

function deserialize(val) {
	if (!val) return "";
	if (typeof val !== "object") return String(val);

	if (val.mode === "variable")
		return `<span data-token-type="variable" data-path="${val.value}" data-label="${
			val.label || ""
		}"></span>`;
	if (val.mode === "formula")
		return `<span data-token-type="formula" data-expression="${
			val.value || ""
		}" data-label="${val.label || ""}" data-config='${JSON.stringify(val.config || null)}'></span>`;
	if (val.mode === "resolver")
		return `<span data-token-type="resolver" data-resolver="${
			val.value || ""
		}" data-label="${val.label || ""}" data-config='${JSON.stringify(val.config || null)}'></span>`;
	if (val.mode === "normalize")
		return `<span data-token-type="normalize" data-expression="${
			val.value || ""
		}" data-label="${val.label || ""}" data-config='${JSON.stringify(val.config || null)}'></span>`;
	if (val.mode === "format")
		return `<span data-token-type="format" data-expression="${
			val.value || ""
		}" data-label="${val.label || ""}" data-config='${JSON.stringify(val.config || null)}'></span>`;

	if (val.mode === "expression" && Array.isArray(val.value)) {
		return val.value
			.map((item) => {
				if (item.type === "text") return item.value;
				if (item.type === "variableToken")
					return `<span data-token-type="variable" data-path="${item.attrs.path}" data-label="${item.attrs.label}"></span>`;
				if (item.type === "formulaToken")
					return `<span data-token-type="formula" data-expression="${
						item.attrs.expression || ""
					}" data-label="${item.attrs.label || ""}" data-config='${JSON.stringify(
						item.attrs.config || null
					)}'></span>`;
				if (item.type === "resolverToken")
					return `<span data-token-type="resolver" data-resolver="${
						item.attrs.resolver || ""
					}" data-label="${item.attrs.label || ""}" data-config='${JSON.stringify(
						item.attrs.config || null
					)}'></span>`;
				if (item.type === "normalizeToken")
					return `<span data-token-type="normalize" data-expression="${
						item.attrs.expression || ""
					}" data-label="${item.attrs.label || ""}" data-config='${JSON.stringify(
						item.attrs.config || null
					)}'></span>`;
				if (item.type === "formatToken")
					return `<span data-token-type="format" data-expression="${
						item.attrs.expression || ""
					}" data-label="${item.attrs.label || ""}" data-config='${JSON.stringify(
						item.attrs.config || null
					)}'></span>`;
				return "";
			})
			.join("");
	}

	return val.value || "";
}

function emitChanges() {
	emitting = true;
	const output = serialize();
	emit("update:modelValue", output);
	emit("update", output);
	nextTick(() => {
		emitting = false;
	});
}

// ── Orchestration ──

function onWrapClick() {
	if (isDynamicMode.value || !isStaticSupported.value) editor.commands.focus();
}

function toggleDynamicMode() {
	if (isReadOnly.value || props.disabled) return;
	isDynamicMode.value = !isDynamicMode.value;
	if (isDynamicMode.value) {
		emitting = true;
		editor.commands.setContent(String(staticValue.value || ""));
		emitting = false;
		nextTick(() => editor.commands.focus());
	} else {
		const struct = serialize();
		staticValue.value = struct.mode === "static" ? struct.value : "";
		emitChanges();
	}
}

function onStaticKeydown(e) {
	if (isReadOnly.value || props.disabled || isDynamicMode.value || !isStaticSupported.value)
		return;
	if (e.key === "@" || e.key === "/") {
		e.preventDefault();
		e.stopPropagation();
		isDynamicMode.value = true;
		nextTick(() => {
			emitting = true;
			editor.commands.setContent("");
			emitting = false;
			editor.commands.focus();
			editor.commands.insertContent(e.key);
		});
	}
}

function updateStaticValue(val) {
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

	if (node.type.name === "formulaToken") {
		activeTokenType.value = "formula";
		tokenDraftAttrs.value = {
			expression: node.attrs.expression,
			label: node.attrs.label,
			config: node.attrs.config || null,
		};
	} else if (node.type.name === "resolverToken") {
		activeTokenType.value = "resolver";
		tokenDraftAttrs.value = {
			resolver: node.attrs.resolver,
			label: node.attrs.label,
			config: node.attrs.config || null,
		};
	} else if (node.type.name === "normalizeToken") {
		activeTokenType.value = "normalize";
		tokenDraftAttrs.value = {
			expression: node.attrs.expression,
			label: node.attrs.label,
			config: node.attrs.config || null,
		};
	} else if (node.type.name === "formatToken") {
		activeTokenType.value = "format";
		tokenDraftAttrs.value = {
			expression: node.attrs.expression,
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
}

function handleBuilderUpdate(config) {
	tokenDraftAttrs.value.config = config;
	tokenDraftAttrs.value.expression = compileToCode(config);
	tokenDraftAttrs.value.label = compileToLabel(config);
}

function saveTokenEditor() {
	if (activeTokenType.value === "json") {
		emitting = true;
		editor.commands.setContent(tokenDraftAttrs.value.value);
		emitting = false;
		emitChanges();
	} else {
		if (isManualMode.value) {
			tokenDraftAttrs.value.config = null;
		}

		emitting = true;
		editor
			.chain()
			.focus()
			.setNodeSelection(activeTokenPos.value)
			.updateAttributes(activeTokenNode.value.type.name, tokenDraftAttrs.value)
			.run();
		emitting = false;
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
		if (emitting) return;
		if (val && typeof val === "object" && val.mode && val.mode !== "static") {
			isDynamicMode.value = true;
			emitting = true;
			editor.commands.setContent(deserialize(val));
			emitting = false;
		} else {
			isDynamicMode.value = false;
			staticValue.value = val?.value ?? val ?? "";
		}
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
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
	min-height: 32px;
	border: 1px solid var(--fxr-border, #e2e8f0);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-bg-input, #fff);
	transition: all 0.2s ease;
}

.fvc-main-field:focus-within {
	border-color: var(--fxr-accent, #2490ef);
	box-shadow: var(--fxr-shadow-focus);
}

/* Deep override to remove internal borders from nested controls in static mode */
.fvc-static-container :deep(.combobox-wrapper),
.fvc-static-container :deep(.form-control),
.fvc-static-container :deep(.fxr-input),
.fvc-static-container :deep(.fxr-input-group),
.fvc-static-container :deep(.fxr-select) {
	border: none !important;
	box-shadow: none !important;
	background: transparent !important;
	height: var(--fxr-input-height, 30px) !important;
	margin-bottom: 0 !important;
	padding-bottom: 0 !important;
}

.fvc-static-container :deep(.fxr-input),
.fvc-static-container :deep(.fxr-select),
.fvc-static-container :deep(.combobox-input) {
	padding: 0 10px !important;
}

.fvc-static-container {
	display: flex;
	align-items: center;
	flex: 1;
	height: 100%;
	min-width: 0;
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
	border-left: 1px solid var(--fxr-border, #e2e8f0);
	margin-left: 4px;
	height: 24px;
	display: flex;
	align-items: center;
}
.fvc-toggle-btn {
	background: transparent;
	border: none;
	cursor: pointer;
	color: #64748b;
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 4px;
	transition: all 0.2s;
}
.fvc-toggle-btn:hover {
	background: #f1f5f9;
	color: #2490ef;
}

.fvc-empty-hint {
	position: absolute;
	top: 3px;
	left: 0;
	color: #94a3b8;
	font-size: 11px;
	pointer-events: none;
	white-space: nowrap;
	font-family: var(--font-stack-mono, monospace);
}
.fvc-empty-hint .hint-part {
	color: #64748b;
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
	top: 3px;
	left: 0;
	color: #cbd5e1;
	font-size: 12px;
	font-style: italic;
	pointer-events: none;
}
.fvc-tiptap-editor :deep(.ProseMirror) {
	outline: none;
	font-size: 13px;
	min-height: 22px;
	white-space: nowrap;
}

.fvc-inline-actions {
	position: absolute;
	right: 0;
	top: 50%;
	transform: translateY(-50%);
	display: flex;
	padding-right: 4px;
	background: linear-gradient(to left, var(--fxr-bg-input, #fff) 80%, transparent);
	z-index: 5;
}

.fvc-action-btn {
	background: transparent;
	border: none !important;
	outline: none !important;
	box-shadow: none !important;
	color: var(--fxr-text-muted, #94a3b8);
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
	color: var(--fxr-accent, #2490ef);
	background: var(--fxr-bg-hover, #f1f5f9);
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
	background: #ecfdf5;
	color: #059669;
	border: 1px solid #10b98133;
}
:deep(.token-formula) {
	background: #f5f3ff;
	color: #7c3aed;
	border: 1px solid #8b5cf633;
}
:deep(.token-normalize) {
	background: #ecfeff;
	color: #0891b2;
	border: 1px solid #06b6d433;
}
:deep(.token-format) {
	background: #fff1f2;
	color: #e11d48;
	border: 1px solid #f43f5e33;
}
:deep(.token-resolver) {
	background: #fffbeb;
	color: #d97706;
	border: 1px solid #f59e0b33;
}

.fxr-token-modal-overlay {
	position: fixed;
	inset: 0;
	background: rgba(15, 23, 42, 0.4);
	backdrop-filter: blur(8px);
	z-index: 13000;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 16px;
}
.fxr-token-modal-container {
	background: #fff;
	border-radius: 12px;
	width: 100%;
	max-width: 580px;
	overflow: hidden;
	box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
	border: 1px solid #e2e8f0;
}
.fxr-token-modal-header {
	height: 52px;
	padding: 0 16px;
	border-bottom: 1px solid #e2e8f0;
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
	border-top: 1px solid #e2e8f0;
	display: flex;
	justify-content: flex-end;
	gap: 8px;
	background: #f8fafc;
	align-items: center;
}

.formula-textarea {
	width: 100%;
	min-height: 120px;
	font-family: monospace;
	padding: 8px;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	font-size: 13px;
	line-height: 1.5;
}
.variables-pill-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	margin-top: 8px;
	max-height: 140px;
	overflow-y: auto;
	padding: 4px;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	background: #f8fafc;
}
.var-pill-btn {
	background: #fff;
	border: 1px solid #cbd5e1;
	padding: 3px 8px;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s;
}
.var-pill-btn:hover {
	background: #f1f5f9;
	border-color: #94a3b8;
}
.json-textarea {
	width: 100%;
	min-height: 200px;
	font-family: monospace;
	font-size: 12px;
}
</style>
