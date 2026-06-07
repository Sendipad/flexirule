<template>
	<div class="tgc-wrap" :class="{ 'is-nested': isNested }" @focusin="onFocusIn">
		<!-- Main Editor Container -->
		<div
			class="tgc-editor-container"
			:class="{ 'nested-container': isNested, 'has-panel': !!activeLogicNode }"
		>
			<!-- Production-Ready Floating Menu (Complete Formatting) -->
			<div v-if="showBubbleMenu" class="tgc-bubble-menu-fixed" :style="bubbleMenuStyle">
				<div class="menu-group">
					<button
						@click="editor.chain().focus().toggleBold().run()"
						:class="{ 'is-active': editor?.isActive('bold') }"
						v-tooltip="__('Bold')"
					>
						<i class="fa fa-bold"></i>
					</button>
					<button
						@click="editor.chain().focus().toggleItalic().run()"
						:class="{ 'is-active': editor?.isActive('italic') }"
						v-tooltip="__('Italic')"
					>
						<i class="fa fa-italic"></i>
					</button>
					<button
						@click="editor.chain().focus().toggleUnderline().run()"
						:class="{ 'is-active': editor?.isActive('underline') }"
						v-tooltip="__('Underline')"
					>
						<i class="fa fa-underline"></i>
					</button>
					<button
						@click="editor.chain().focus().toggleStrike().run()"
						:class="{ 'is-active': editor?.isActive('strike') }"
						v-tooltip="__('Strikethrough')"
					>
						<i class="fa fa-strikethrough"></i>
					</button>
					<button
						@click="editor.chain().focus().toggleCode().run()"
						:class="{ 'is-active': editor?.isActive('code') }"
						v-tooltip="__('Code')"
					>
						<i class="fa fa-code"></i>
					</button>
				</div>
				<div class="menu-group">
					<button
						@click="editor.chain().focus().toggleTranslation().run()"
						:class="{ 'is-active': editor?.isActive('translation') }"
						v-tooltip="__('Translate')"
					>
						<i class="fa fa-language"></i>
					</button>
					<button @click="insertTrigger('@')" v-tooltip="__('Insert Variable')">
						<i class="fa fa-at"></i>
					</button>
					<button @click="insertTrigger('/')" v-tooltip="__('Insert Logic')">
						<i class="fa fa-terminal"></i>
					</button>
				</div>
				<div class="divider"></div>
				<button
					@click="editor.chain().focus().unsetAllMarks().run()"
					class="btn-clear"
					v-tooltip="__('Clear Formatting')"
				>
					<i class="fa fa-eraser"></i>
				</button>
			</div>

			<!-- ── Visual Editor ── -->
			<div v-show="mode === 'visual'" class="tgc-body visual-body">
				<div class="tgc-editor-wrapper v2-scrollbar">
					<editor-content :editor="editor" class="tgc-tiptap-editor" />
					<div v-if="!readOnly && isEditorEmpty" class="tgc-empty-hint">
						{{ __("Type '@' or '/' to begin...") }}
					</div>
				</div>

				<!-- Logic Settings Panel -->
				<transition name="panel-slide">
					<div v-if="activeLogicNode && !isNested" class="tgc-bottom-panel">
						<div class="panel-header">
							<div class="panel-icon" :class="activeLogicNode.attrs.type">
								<i
									:class="
										activeLogicNode.attrs.type === 'conditional'
											? 'fa fa-code-fork'
											: 'fa fa-refresh'
									"
								></i>
							</div>
							<div class="panel-title-group">
								<span class="panel-title">{{
									activeLogicNode.attrs.type === "conditional"
										? __("CONDITION EDITOR")
										: __("LOOP EDITOR")
								}}</span>
								<span class="panel-subtitle">{{
									activeLogicNode.attrs._raw_expr ||
									activeLogicNode.attrs.iterable
								}}</span>
							</div>
							<div class="panel-actions ml-auto">
								<button class="btn-modern-danger" @click="deleteActiveNode">
									<i class="fa fa-trash"></i>
								</button>
								<button class="btn-modern-close" @click="closeDrawer">
									<i class="fa fa-times"></i>
								</button>
							</div>
						</div>

						<div class="panel-body v2-scrollbar" :key="activeLogicNode.pos">
							<div class="panel-grid">
								<template v-if="activeLogicNode.attrs.type === 'conditional'">
									<div class="grid-item full-width">
										<ConditionBuilder
											:modelValue="activeLogicNode.attrs.condition"
											:docFields="docFieldOptions"
											:variableOptions="dynamicRoots"
											:readOnly="readOnly"
											@update:modelValue="onConditionUpdate"
										/>
									</div>
									<div class="grid-item full-width mt-2">
										<label class="compact-label">{{
											__("IF TRUE (THEN CONTENT)")
										}}</label>
										<TextGeneratorControl
											:modelValue="activeLogicNodeThen"
											:isNested="true"
											:variableOptions="dynamicRoots"
											@update:modelValue="updateActiveNodeThen"
										/>
									</div>
									<div class="grid-item full-width mt-2">
										<label class="compact-label">{{
											__("IF FALSE (ELSE CONTENT)")
										}}</label>
										<TextGeneratorControl
											:modelValue="activeLogicNodeElse"
											:isNested="true"
											:variableOptions="dynamicRoots"
											@update:modelValue="updateActiveNodeElse"
										/>
									</div>
								</template>

								<template v-else-if="activeLogicNode.attrs.type === 'loop'">
									<div class="grid-item full-width">
										<div class="loop-meta-row">
											<div class="meta-field">
												<label class="compact-label">{{
													__("ITERATOR")
												}}</label>
												<input
													class="form-control input-sm"
													:value="activeLogicNode.attrs.iterator"
													@input="
														updateActiveNode({
															iterator: $event.target.value,
														})
													"
													placeholder="item"
												/>
											</div>
											<div class="meta-field flex-1">
												<label class="compact-label">{{
													__("COLLECTION")
												}}</label>
												<ComboBoxControl
													:df="{ fieldtype: 'Autocomplete' }"
													:options="collectionOptions"
													:modelValue="activeLogicNode.attrs.iterable"
													:read_only="readOnly"
													:hideLabel="true"
													@update:modelValue="
														updateActiveNode({ iterable: $event })
													"
												/>
											</div>
										</div>
									</div>
									<div class="grid-item full-width mt-3">
										<label class="compact-label">{{ __("LOOP BODY") }}</label>
										<TextGeneratorControl
											:modelValue="activeLogicNodeLoop"
											:isNested="true"
											:variableOptions="dynamicRoots"
											@update:modelValue="updateActiveNodeLoop"
										/>
									</div>
								</template>
							</div>
						</div>
					</div>
				</transition>
			</div>

			<!-- ── Raw Mode ── -->
			<div v-show="mode === 'raw'" class="tgc-body raw-body">
				<textarea
					ref="rawTextareaRef"
					class="tgc-raw-textarea"
					v-model="rawJinja"
					:readonly="readOnly"
					spellcheck="false"
					@keydown.tab.prevent="insertTabInRaw"
				></textarea>
			</div>
		</div>

		<!-- Unified Footer Toolbar -->
		<div class="tgc-footer-toolbar" v-if="!isNested">
			<div class="footer-left">
				<div class="tgc-mode-tabs" v-if="!readOnly">
					<button
						class="tgc-mode-tab"
						:class="{ active: mode === 'visual' }"
						@click="switchMode('visual')"
					>
						<i class="fa fa-th-large"></i> {{ __("Visual") }}
					</button>
					<button
						class="tgc-mode-tab"
						:class="{ active: mode === 'raw' }"
						@click="switchMode('raw')"
					>
						<i class="fa fa-code"></i> {{ __("Jinja") }}
					</button>
				</div>
				<div class="tgc-rich-actions" v-if="mode === 'visual' && !readOnly">
					<button
						class="action-btn-mini"
						@click="insertTrigger('@')"
						v-tooltip="__('Variable')"
					>
						<i class="fa fa-at"></i>
					</button>
					<button
						class="action-btn-mini"
						@click="insertTrigger('/')"
						v-tooltip="__('Logic')"
					>
						<i class="fa fa-terminal"></i>
					</button>
				</div>
				<div class="divider-v"></div>
				<div class="legend-pills">
					<span class="pill-mini if">IF</span> <span class="pill-mini loop">FOR</span>
					<span class="pill-mini var">@</span>
				</div>
			</div>

			<div class="footer-right">
				<div class="tgc-preview-toggle mr-3" v-if="mode === 'visual'">
					<span class="tgc-switch-label mr-1">{{ __("Preview") }}</span>
					<label class="tgc-switch mini">
						<input type="checkbox" v-model="previewMode" />
						<span class="tgc-slider"></span>
					</label>
				</div>
				<div class="stats-mini">
					{{ charCount }} {{ __("chars") }} • {{ nodeCount }} {{ __("nodes") }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount, nextTick, shallowRef } from "vue";
import { Editor, EditorContent, VueRenderer } from "@tiptap/vue-3";
import { StarterKit } from "@tiptap/starter-kit";
import tippy from "tippy.js";

import {
	LogicNode,
	VariableNode,
	VariableTrigger,
	LogicTrigger,
	VarPluginKey,
	LogicPluginKey,
	TranslationMark,
} from "../utils/tiptap_extensions";
import MentionList from "./MentionList.vue";
import ConditionBuilder from "../components/condition_builder/ConditionBuilder.vue";
import ComboBoxControl from "./ComboBoxControl.vue";

import {
	compileSegmentsToJinja,
	parseJinjaToSegments,
	convertSegmentsToHtml,
	convertHtmlToSegments,
	serializeCondition,
} from "../utils/text_generator";
import { setActiveTGC } from "../utils/tgc_focus";

const props = defineProps({
	df: { type: Object, default: null },
	modelValue: { type: [Object, String], default: null },
	templateValue: { type: String, default: "" },
	read_only: { type: Boolean, default: false },
	variableOptions: { type: [Array, Object], default: () => [] },
	docFieldOptions: { type: Array, default: () => [] },
	isNested: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const readOnly = computed(() => !!props.read_only || !!props.df?.read_only);
const mode = ref("visual");
const rawJinja = ref("");
const ui = ref({ version: 2, segments: [] });
const previewMode = ref(false);
const activeLogicNode = ref(null);
const activeSegKey = ref(null);
const activeLogicNodeThen = ref({ version: 2, segments: [] });
const activeLogicNodeElse = ref({ version: 2, segments: [] });
const activeLogicNodeLoop = ref({ version: 2, segments: [] });
const showElse = ref(false);
let emitting = false;

const normalizedVariableOptions = computed(() => {
	const source = props.variableOptions;
	if (Array.isArray(source)) return source;
	if (Array.isArray(source?.value)) return source.value;
	if (Array.isArray(source?.options)) return source.options;
	return [];
});

// ─── Production-Ready Floating Menu Logic ───
const showBubbleMenu = ref(false);
const bubbleMenuStyle = ref({ top: "0px", left: "0px", position: "fixed" });
const selectionTrigger = ref(0);
const getActiveIterators = () => {
	if (!editor || selectionTrigger.value < 0) return [];
	const { from } = editor.state.selection;
	const iters = [];

	editor.state.doc.descendants((node, pos) => {
		if (pos >= from) return false;
		if (node.type.name === "logic") {
			const { isStart, isElse, type, iterator, iterable } = node.attrs;
			if (type === "loop") {
				if (isStart) iters.push({ iterator, iterable });
				else if (!isStart && !isElse) iters.pop();
			}
		}
	});
	return iters;
};

const dynamicRoots = computed(() => {
	// Dependency on selectionTrigger to force re-calc
	selectionTrigger.value;
	const active = getActiveIterators();
	const roots = [...normalizedVariableOptions.value];

	active.forEach(({ iterator, iterable }) => {
		if (!iterator) return;

		// 1. Resolve children properties of the collection and map them to the iterator
		if (iterable) {
			const iterableSuffix = String(iterable).split(".").pop(); // e.g. "items" from "doc.items"
			const prefix1 = iterable + "."; // e.g. "doc.items."
			const prefix2 = iterableSuffix + "."; // e.g. "items."

			const childFields = roots.filter((r) => {
				const val = r.value || r;
				return (
					typeof val === "string" && (val.startsWith(prefix1) || val.startsWith(prefix2))
				);
			});

			// Add iterator child fields
			childFields.forEach((child) => {
				const val = child.value || child;
				let suffix = val;
				if (val.startsWith(prefix1)) suffix = val.slice(prefix1.length);
				else if (val.startsWith(prefix2)) suffix = val.slice(prefix2.length);

				const iterValue = `${iterator}.${suffix}`;
				if (!roots.find((r) => (r.value || r) === iterValue)) {
					roots.unshift({
						...child,
						label: `${iterator}.${suffix} (${child.label || suffix})`,
						value: iterValue,
						is_iterator_child: true,
						is_iterator: false,
					});
				}
			});
		}

		// 2. Always add the root iterator variable itself
		if (!roots.find((r) => (r.value || r) === iterator)) {
			roots.unshift({ label: iterator, value: iterator, is_iterator: true });
		}
	});

	return roots;
});

const editor = new Editor({
	extensions: [
		StarterKit.configure({
			heading: { levels: [1, 2, 3] },
			codeBlock: false,
			blockquote: false,
		}),
		VariableNode,
		LogicNode,
		TranslationMark,
		VariableTrigger.configure({
			suggestion: {
				char: "@",
				pluginKey: VarPluginKey,
				command: ({ editor, range, props }) => {
					editor
						.chain()
						.focus()
						.insertContentAt(range, [
							{ type: "variable", attrs: { path: props.id, label: props.label } },
						])
						.run();
				},
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					return dynamicRoots.value
						.map((v, idx) => ({
							id: v.value || v,
							label: v.label || v,
							type: "variable",
							is_loop_scoped: !!v.is_loop_scoped,
							_origIdx: idx,
						}))
						.filter((v) => v.id.toLowerCase().includes(q))
						.sort((a, b) => {
							if (a.is_loop_scoped && !b.is_loop_scoped) return -1;
							if (!a.is_loop_scoped && b.is_loop_scoped) return 1;
							return a._origIdx - b._origIdx;
						})
						.slice(0, 50);
				},
			},
		}),
		LogicTrigger.configure({
			suggestion: {
				char: "/",
				pluginKey: LogicPluginKey,
				command: ({ editor, range, props }) => {
					const type = props.id === "if" ? "conditional" : "loop";
					const key = Math.random().toString(36).slice(2, 9);
					const content = [
						{
							type: "logic",
							attrs: {
								type,
								isStart: true,
								_key: key,
								condition:
									type === "conditional" ? { op: "and", conditions: [] } : null,
								iterator: type === "loop" ? "item" : "",
								iterable: "",
							},
						},
						{ type: "text", text: " " },
					];
					if (type === "conditional") {
						content.push({
							type: "logic",
							attrs: { type, isStart: false, isElse: true, _key: key },
						});
						content.push({ type: "text", text: " " });
					}
					content.push({
						type: "logic",
						attrs: { type, isStart: false, isElse: false, _key: key },
					});
					editor.chain().focus().insertContentAt(range, content).run();
				},
				render: () => createSuggestionRenderer(),
				items: ({ query }) => {
					const q = query.toLowerCase();
					return [
						{ id: "if", label: "IF Condition", type: "logic" },
						{ id: "loop", label: "LOOP Block", type: "logic" },
					].filter((l) => l.label.toLowerCase().includes(q));
				},
			},
		}),
	],
	editable: !readOnly.value,
	onUpdate: ({ editor: ed }) => {
		selectionTrigger.value++;
		if (emitting) return;
		ui.value.segments = convertHtmlToSegments(ed.getHTML());

		if (activeSegKey.value && !props.isNested) {
			const seg = findSegmentByKey(ui.value.segments, activeSegKey.value);
			if (seg) {
				if (seg.type === "conditional") {
					activeLogicNodeThen.value = { version: 2, segments: seg.then_segments || [] };
					activeLogicNodeElse.value = { version: 2, segments: seg.else_segments || [] };
				} else if (seg.type === "loop") {
					activeLogicNodeLoop.value = { version: 2, segments: seg.segments || [] };
				}
			}
		}

		emitChanges();
	},
	onSelectionUpdate: ({ editor: ed }) => {
		selectionTrigger.value++;
		const { from, to } = ed.state.selection;
		if (from === to || readOnly.value || mode.value !== "visual") {
			showBubbleMenu.value = false;
			return;
		}

		const { view } = ed;
		try {
			const start = view.coordsAtPos(from);
			const end = view.coordsAtPos(to);

			showBubbleMenu.value = true;
			bubbleMenuStyle.value = {
				top: `${Math.min(start.top, end.top) - 48}px`,
				left: `${(start.left + end.left) / 2}px`,
				position: "fixed",
				transform: "translateX(-50%)",
			};
		} catch (e) {
			showBubbleMenu.value = false;
		}
	},
	editorProps: {
		handleClick(view, pos, event) {
			const { state } = view;
			let resolvedPos = pos;
			let node = state.doc.nodeAt(resolvedPos);
			if (!node || node.type.name !== "logic") {
				node = state.doc.nodeAt(resolvedPos - 1);
				if (node?.type.name === "logic") resolvedPos--;
			}
			if (node?.type.name === "logic" && (node.attrs.isStart || node.attrs.isElse)) {
				activeLogicNode.value = null;
				nextTick(() => {
					activeLogicNode.value = { node, pos: resolvedPos, attrs: { ...node.attrs } };
					activeSegKey.value = node.attrs._key;

					const seg = findSegmentByKey(ui.value.segments, node.attrs._key);
					if (seg) {
						if (node.attrs.type === "conditional") {
							activeLogicNodeThen.value = {
								version: 2,
								segments: seg.then_segments || [],
							};
							activeLogicNodeElse.value = {
								version: 2,
								segments: seg.else_segments || [],
							};
						} else {
							activeLogicNodeLoop.value = {
								version: 2,
								segments: seg.segments || [],
							};
						}
					}

					showElse.value = true;
				});
				return true;
			}
			return false;
		},
	},
});

function createSuggestionRenderer() {
	let component;
	let popup;
	return {
		onStart: (props) => {
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
			popup?.destroy();
			component?.destroy();
		},
	};
}

const charCount = computed(() => editor.getText().length);
const nodeCount = computed(() => ui.value.segments.length);
const isEditorEmpty = computed(() => editor.isEmpty);
function closeDrawer() {
	activeLogicNode.value = null;
}
function getFieldLabel(path) {
	const opt = dynamicRoots.value.find((o) => (o.value || o) === path);
	return opt ? opt.label || path : path;
}

function updateActiveNode(attrs) {
	if (!activeLogicNode.value) return;
	const { pos } = activeLogicNode.value;

	if (attrs.condition) {
		let fieldLabel = "";
		if (attrs.condition?.left?.ref) fieldLabel = getFieldLabel(attrs.condition.left.ref);
		else if (attrs.condition?.conditions?.[0]?.left?.ref)
			fieldLabel = getFieldLabel(attrs.condition.conditions[0].left.ref);
		attrs.label = fieldLabel;
	} else if (attrs.iterable) {
		attrs.label = getFieldLabel(attrs.iterable);
	}

	activeLogicNode.value.attrs = { ...activeLogicNode.value.attrs, ...attrs };
	editor.chain().focus().setNodeSelection(pos).updateAttributes("logic", attrs).run();
}
function onConditionUpdate(condition) {
	updateActiveNode({ condition, _raw_expr: serializeCondition(condition) });
}
function deleteActiveNode() {
	if (!activeLogicNode.value) return;
	editor.chain().focus().setNodeSelection(activeLogicNode.value.pos).deleteSelection().run();
	closeDrawer();
}

function findSegmentByKey(segs, key) {
	if (!segs || !key) return null;
	for (const seg of segs) {
		if (seg._key === key) return seg;
		if (seg.then_segments) {
			const f = findSegmentByKey(seg.then_segments, key);
			if (f) return f;
		}
		if (seg.else_segments) {
			const f = findSegmentByKey(seg.else_segments, key);
			if (f) return f;
		}
		if (seg.segments) {
			const f = findSegmentByKey(seg.segments, key);
			if (f) return f;
		}
	}
	return null;
}

function _syncNestedToMain() {
	emitting = true;
	editor.commands.setContent(convertSegmentsToHtml(ui.value.segments, dynamicRoots.value));

	if (activeSegKey.value && activeLogicNode.value) {
		editor.state.doc.descendants((n, p) => {
			if (n.type.name === "logic" && n.attrs._key === activeSegKey.value && n.attrs.isStart) {
				activeLogicNode.value.pos = p;
				return false;
			}
		});
	}

	emitting = false;
	emitChanges();
}

function updateActiveNodeThen(val) {
	const seg = findSegmentByKey(ui.value.segments, activeSegKey.value);
	if (seg) {
		seg.then_segments = val.segments;
		activeLogicNodeThen.value = val;
		_syncNestedToMain();
	}
}

function updateActiveNodeElse(val) {
	const seg = findSegmentByKey(ui.value.segments, activeSegKey.value);
	if (seg) {
		seg.else_segments = val.segments;
		activeLogicNodeElse.value = val;
		_syncNestedToMain();
	}
}

function updateActiveNodeLoop(val) {
	const seg = findSegmentByKey(ui.value.segments, activeSegKey.value);
	if (seg) {
		seg.segments = val.segments;
		activeLogicNodeLoop.value = val;
		_syncNestedToMain();
	}
}
function insertTrigger(char) {
	editor.chain().focus().insertContent(char).run();
}
const collectionOptions = computed(() =>
	dynamicRoots.value.filter((o) => o.fieldtype === "Table" || o.is_list)
);
function emitChanges() {
	emitting = true;
	emit("update:modelValue", JSON.parse(JSON.stringify(ui.value)));
	nextTick(() => (emitting = false));
}
function switchMode(m) {
	if (m === mode.value) return;
	if (m === "raw") rawJinja.value = compileSegmentsToJinja(ui.value.segments);
	else {
		const segs = parseJinjaToSegments(rawJinja.value);
		ui.value.segments = segs;
		editor.commands.setContent(convertSegmentsToHtml(segs, dynamicRoots.value));
	}
	mode.value = m;
}
watch(
	() => props.modelValue,
	(val) => {
		if (emitting) return;
		const norm = normalizeModel(val || props.templateValue);
		ui.value = norm;
		editor.commands.setContent(convertSegmentsToHtml(norm.segments, dynamicRoots.value));
	},
	{ immediate: true, deep: true }
);
function normalizeModel(val) {
	if (val?.segments) return val;
	if (typeof val === "string") return { version: 2, segments: parseJinjaToSegments(val) };
	return { version: 2, segments: [] };
}
function onFocusIn() {
	if (props.isNested) return;
	setActiveTGC((p) =>
		editor
			.chain()
			.focus()
			.insertContent([{ type: "variable", attrs: { path: p } }])
			.run()
	);
}
onBeforeUnmount(() => {
	editor.destroy();
});
</script>

<style scoped>
.tgc-wrap {
	display: flex;
	flex-direction: column;
	gap: 6px;
	background: color-mix(in srgb, var(--fxr-surface, #fff) 94%, var(--fxr-surface-2, #f3f5f7));
	padding: 8px;
	border-radius: 12px;
	border: 1px solid var(--fxr-border-subtle);
}
.tgc-wrap.is-nested {
	padding: 0;
	background: transparent;
	border: none;
}

.tgc-editor-container {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 10px;
	background: var(--fxr-surface, #fff);
	overflow: hidden;
	min-height: 120px;
	position: relative;
	box-shadow: var(--fxr-shadow-sm);
	transition:
		border-color var(--fxr-transition-fast),
		box-shadow var(--fxr-transition-fast);
}

.tgc-editor-container:focus-within {
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-focus);
}
.tgc-editor-wrapper {
	padding: 12px 12px 10px;
	min-height: 120px;
	position: relative;
}
.tgc-empty-hint {
	position: absolute;
	top: 12px;
	left: 12px;
	color: var(--fxr-text-faint, #cbd5e1);
	font-size: 13px;
	pointer-events: none;
}

.tgc-tiptap-editor :deep(.ProseMirror) {
	outline: none;
	line-height: 1.6;
	font-size: 14px;
	color: var(--fxr-text-strong, #1e293b);
	min-height: 100px;
	unicode-bidi: plaintext;
	text-align: start;
}

/* ── Badges (Ultra-Compact) ── */
:deep(.tg-badge) {
	display: inline-flex;
	align-items: center;
	padding: 0px 6px;
	border-radius: 4px;
	font-size: 10px;
	font-weight: 800;
	margin: 1px 2px;
	cursor: pointer;
	border: 1px solid transparent;
	transition: all 0.2s;
	white-space: nowrap;
	max-width: 200px;
	overflow: hidden;
	text-overflow: ellipsis;
	vertical-align: middle;
	line-height: 1.6;
}
:deep(.tg-badge-var) {
	background: var(--fxr-badge-bool);
	color: var(--fxr-badge-bool-text);
	border-color: rgba(16, 185, 129, 0.2);
}
:deep(.tg-badge-if) {
	background: var(--fxr-badge-var);
	color: var(--fxr-badge-var-text);
	border-color: rgba(124, 58, 237, 0.2);
}
:deep(.tg-badge-loop) {
	background: var(--fxr-badge-normalize);
	color: var(--fxr-badge-normalize-text);
	border-color: rgba(37, 99, 235, 0.2);
}
:deep(.tg-badge-else) {
	background: var(--fxr-badge-resolver);
	color: var(--fxr-badge-resolver-text);
	border-color: rgba(217, 119, 6, 0.2);
}
:deep(.tg-badge-trans) {
	background: color-mix(in srgb, var(--fxr-accent-soft, #e0f2fe) 88%, var(--fxr-surface));
	color: var(--cyan-700, #0284c7);
	border-color: color-mix(in srgb, var(--cyan-500, #0ea5e9) 24%, var(--fxr-surface));
}
:deep(.tg-badge-end) {
	background: var(--fxr-surface-2, #f1f5f9);
	color: var(--fxr-text-faint, #94a3b8);
	padding: 0 4px;
	font-family: monospace;
	border: none;
	min-width: 12px;
	justify-content: center;
	font-weight: 800;
	opacity: 0.6;
}

/* ── Bubble Menu (Fixed Position) ── */
.tgc-bubble-menu-fixed {
	display: flex;
	background: color-mix(in srgb, var(--fxr-text-strong, #1e293b) 92%, var(--fxr-text));
	padding: 4px;
	border-radius: 8px;
	box-shadow: var(--fxr-shadow-lg, 0 22px 48px rgba(15, 23, 42, 0.12));
	gap: 2px;
	z-index: 10001;
	align-items: center;
}
.menu-group {
	display: flex;
	gap: 1px;
}
.tgc-bubble-menu-fixed button {
	background: transparent;
	border: none;
	color: var(--fxr-text-faint, #94a3b8);
	width: 28px;
	height: 28px;
	border-radius: 4px;
	cursor: pointer;
	transition: all 0.2s;
	font-size: 11px;
	display: flex;
	align-items: center;
	justify-content: center;
}
.tgc-bubble-menu-fixed button:hover,
.tgc-bubble-menu-fixed button.is-active {
	color: #fff;
	background: color-mix(in srgb, var(--fxr-text-strong, #334155) 78%, var(--fxr-text));
}
.tgc-bubble-menu-fixed .divider {
	width: 1px;
	height: 16px;
	background: color-mix(in srgb, var(--fxr-text-soft, #334155) 70%, var(--fxr-text));
	margin: 0 4px;
}
.btn-clear {
	color: var(--red-400, #f87171) !important;
}

/* ── Footer Toolbar (Unified) ── */
.tgc-footer-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 2px 6px;
	margin-top: 2px;
	background: var(--fxr-surface-2);
	border-radius: 8px;
	min-height: 28px;
	border: 1px solid var(--fxr-border-subtle);
}
.footer-left,
.footer-right {
	display: flex;
	align-items: center;
}

.tgc-mode-tabs {
	display: flex;
	background: var(--fxr-surface-soft, #f1f5f9);
	padding: 2px;
	border-radius: 6px;
}
.tgc-mode-tab {
	padding: 3px 8px;
	font-size: 10px;
	font-weight: 700;
	border: none;
	background: transparent;
	color: var(--fxr-text-soft, #64748b);
	cursor: pointer;
	border-radius: 4px;
	transition: all 0.2s;
}
.tgc-mode-tab.active {
	background: var(--fxr-surface, #fff);
	color: var(--fxr-text-strong, #1e293b);
	box-shadow: var(--fxr-shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.05));
}

.tgc-rich-actions {
	display: flex;
	gap: 2px;
	padding: 0 8px;
	margin-left: 8px;
	border-left: 1px solid var(--fxr-border-subtle, #e2e8f0);
}
.action-btn-mini {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	border: none;
	background: transparent;
	color: var(--fxr-text-soft, #64748b);
	border-radius: 6px;
	cursor: pointer;
	font-size: 11px;
}
.action-btn-mini:hover {
	background: var(--fxr-surface-2, #f1f5f9);
	color: var(--fxr-text-strong, #1e293b);
}

.divider-v {
	width: 1px;
	height: 16px;
	background: var(--fxr-border-subtle, #e2e8f0);
	margin: 0 12px;
}

.legend-pills {
	display: flex;
	gap: 4px;
}
.pill-mini {
	font-size: 8px;
	font-weight: 900;
	padding: 0px 4px;
	border-radius: 3px;
}
.pill-mini.if {
	background: color-mix(in srgb, var(--fxr-accent-soft, #f5f3ff) 92%, var(--fxr-surface));
	color: var(--purple-700, #7c3aed);
}
.pill-mini.loop {
	background: var(--fxr-accent-soft, #eff6ff);
	color: var(--blue-700, #2563eb);
}
.pill-mini.var {
	background: var(--fxr-success-soft, #ecfdf5);
	color: var(--green-700, #059669);
}

.tgc-switch-label {
	font-size: 10px;
	font-weight: 700;
	color: var(--fxr-text-faint, #94a3b8);
}
.stats-mini {
	font-size: 9px;
	font-weight: 700;
	color: var(--fxr-text-faint, #94a3b8);
}

/* ── Bottom Panel ── */
.tgc-bottom-panel {
	border-top: 1px solid var(--fxr-border-subtle, #e2e8f0);
	background: var(--fxr-surface, #fcfcfd);
	display: flex;
	flex-direction: column;
}
.panel-header {
	padding: 6px 12px;
	border-bottom: 1px solid var(--fxr-border-subtle, #f1f5f9);
	display: flex;
	align-items: center;
	gap: 8px;
}
.panel-icon {
	width: 24px;
	height: 24px;
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
}
.panel-icon.conditional {
	background: color-mix(in srgb, var(--fxr-accent-soft, #f5f3ff) 92%, var(--fxr-surface));
	color: var(--purple-700, #7c3aed);
}
.panel-icon.loop {
	background: var(--fxr-accent-soft, #eff6ff);
	color: var(--blue-700, #2563eb);
}
.panel-title {
	font-weight: 800;
	font-size: 11px;
	color: var(--fxr-text-strong, #1e293b);
}
.panel-subtitle {
	font-size: 9px;
	color: var(--fxr-text-faint, #94a3b8);
	font-family: monospace;
	margin-left: 4px;
}
.btn-modern-danger {
	width: 28px;
	height: 28px;
	border-radius: 50%;
	border: none;
	background: transparent;
	color: var(--red-500, #ef4444);
	cursor: pointer;
	font-size: 11px;
}
.btn-modern-danger:hover {
	background: var(--fxr-danger-soft, #fef2f2);
}
.btn-modern-close {
	width: 28px;
	height: 28px;
	border-radius: 50%;
	border: none;
	background: var(--fxr-surface-2, #f1f5f9);
	color: var(--fxr-text-soft, #64748b);
	cursor: pointer;
	font-size: 11px;
}
.btn-modern-close:hover {
	background: color-mix(in srgb, var(--fxr-surface-2, #e2e8f0) 80%, var(--fxr-surface));
	color: var(--fxr-text-strong, #1e293b);
}
.panel-body {
	padding: 8px 12px;
	max-height: 300px;
	overflow-y: auto;
}
.panel-grid {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 8px;
}
.grid-item.full-width {
	grid-column: span 2;
}
.compact-label {
	font-size: 9px;
	font-weight: 800;
	color: var(--fxr-text-faint, #94a3b8);
	text-transform: uppercase;
	margin-bottom: 2px;
	display: block;
}

.panel-slide-enter-active,
.panel-slide-leave-active {
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.panel-slide-enter-from,
.panel-slide-leave-to {
	transform: translateY(100%);
	opacity: 0;
}
.tgc-raw-textarea {
	width: 100%;
	min-height: 200px;
	border: 1px solid var(--fxr-border-subtle, #e2e8f0);
	border-radius: 12px;
	background: var(--fxr-surface, #fff);
	padding: 12px;
	font-size: 13px;
	font-family: monospace;
	line-height: 1.5;
	outline: none;
	resize: none;
}
</style>
