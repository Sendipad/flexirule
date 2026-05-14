<template>
	<div class="set-value-config">
		<div class="config-section section-card header-compact">
			<div class="d-flex align-items-center justify-content-between">
				<h5 class="mb-0">{{ __("Set Value Configuration") }}</h5>
				<span class="text-muted small">{{ __("Define field updates and templates") }}</span>
			</div>
		</div>

		<div class="config-section section-card">
			<div class="form-group mb-3">
				<template v-if="!targetFieldState.hidden">
					<label class="form-label"
						>{{
							getFieldLabel(
								props.node?.data?.action_type || "Set Value",
								"target_field"
							) || __("Target Field")
						}}
						<span v-if="targetFieldState.reqd" class="text-danger">*</span></label
					>
					<template v-if="props.node?.data?.operation === 'Context Variable'">
						<ComboBoxControl
							:df="with_read_only({ label: '', fieldtype: 'Autocomplete' })"
							:modelValue="props.node?.data?.target_field"
							:get_query="async () => variable_options"
							:read_only="readOnly"
							:hideLabel="true"
							@update:modelValue="(val) => update_action_field('target_field', val)"
						/>
						<small class="text-muted">{{
							__("Variable path to update (e.g. vars.loop.full_name)")
						}}</small>
					</template>
					<template v-else>
						<ComboBoxControl
							:df="with_read_only({ label: '', fieldtype: 'FieldPicker' })"
							:options="doctype_fields"
							:doctype="reference_doctype"
							:modelValue="props.node?.data?.target_field"
							:read_only="readOnly"
							:trigger="'button'"
							:hideLabel="true"
							@update:modelValue="(val) => update_action_field('target_field', val)"
						/>
						<small class="text-muted">{{
							__("The document field that will be updated")
						}}</small>
					</template>
				</template>
			</div>

			<div class="form-group mb-3">
				<TextGeneratorControl
					:df="with_read_only(textGeneratorField)"
					:modelValue="config.text_generator_ui"
					:read_only="readOnly"
					:variableOptions="variable_options"
					:docFieldOptions="doctype_fields"
					@update:modelValue="update_template_ui"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import ControlFactory from "../../../controls/ControlFactory.vue";
import TextGeneratorControl from "../../../controls/TextGeneratorControl.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { getDerivedFieldState, getFieldLabel } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const {
	config,
	doctype_fields,
	variable_options,
	reference_doctype,
	with_read_only,
	update_action_field,
	sync_config,
	store,
} = useActionConfig(props);

const valueTemplateState = computed(() =>
	getDerivedFieldState(
		props.node?.data?.action_type || "Set Value",
		"value_template",
		props.node?.data || {},
		store.rule_doc || {},
		{
			operation: props.node?.data?.operation,
			processName: props.node?.data?.process_name,
		}
	)
);

const textGeneratorField = computed(() => ({
	fieldname: "text_generator_ui",
	fieldtype: "Text Generator",
	label:
		getFieldLabel(props.node?.data?.action_type || "Set Value", "value_template") ||
		__("Value Builder"),
	reqd: valueTemplateState.value.reqd ? 1 : 0,
}));

const targetFieldState = computed(() =>
	getDerivedFieldState(
		props.node?.data?.action_type || "Set Value",
		"target_field",
		props.node?.data || {},
		store.rule_doc || {},
		{
			operation: props.node?.data?.operation,
			processName: props.node?.data?.process_name,
		}
	)
);

function update_template_ui(value) {
	config.text_generator_ui = value;
	const knownVarRoots = (variable_options.value || [])
		.map((v) => String(v?.value || ""))
		.filter((p) => p.startsWith("vars."))
		.map((p) => p.slice(5).split(".")[0]);
	// Compile segments to Jinja and store in value_template
	const jinja = compileSegmentsToJinja(value?.segments || [], { knownVarRoots });
	update_action_field("value_template", jinja);
	sync_local_config();
	store.mark_dirty();
}

function load_local_config(val) {
	let parsed = {};
	if (typeof val === "string") {
		try {
			parsed = JSON.parse(val);
		} catch (e) {
			parsed = {};
		}
	} else if (val && typeof val === "object") {
		parsed = val;
	}

	// Backwards compat: if no text_generator_ui but value_template exists, create a text segment
	if (!parsed.text_generator_ui && props.node?.data?.value_template) {
		parsed.text_generator_ui = {
			version: 2,
			segments: [{ type: "text", content: props.node.data.value_template }],
		};
	}

	// Compare with current local state to avoid re-triggering watchers
	const current_str = JSON.stringify(config);
	const next_str = JSON.stringify(parsed);
	if (current_str === next_str) return;

	Object.keys(config).forEach((key) => delete config[key]);
	Object.assign(config, parsed);
}

function sync_local_config() {
	const next_config = {};
	for (const [key, value] of Object.entries(config)) {
		if (value !== undefined && value !== null && value !== "") {
			next_config[key] = value;
		}
	}

	// sync_config in useActionConfig already performs a string compare against props.node.data.config
	sync_config(next_config);
}

watch(
	() => props.node?.data?.config,
	(val) => load_local_config(val),
	{ immediate: true, deep: true }
);

watch(
	() => config,
	() => sync_local_config(),
	{ deep: true }
);

function validate() {
	const errors = [];
	if (targetFieldState.value.reqd && !props.node?.data?.target_field) {
		errors.push(__("Target Field is required"));
	}
	const ui = config.text_generator_ui;
	if (!ui || !Array.isArray(ui.segments) || !ui.segments.length) {
		errors.push(__("Value Builder content is required"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.set-value-config {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.section-card {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 12px;
	background: var(--bg-light, #fff);
}

.form-label {
	font-weight: 500;
	margin-bottom: 6px;
	display: block;
	font-size: 13px;
}
</style>
