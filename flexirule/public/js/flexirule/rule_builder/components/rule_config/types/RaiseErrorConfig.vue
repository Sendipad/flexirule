<template>
	<div class="raise-error-config">
		<div class="config-section section-card">
			<div class="form-group mb-3">
				<ControlFactory
					:df="with_read_only(errorTypeField)"
					:modelValue="config.error_type || 'Validation Error'"
					@update:modelValue="(val) => update_config_key('error_type', val)"
				/>
			</div>

			<div class="form-group mb-3">
				<ControlFactory
					:df="with_read_only(errorTitleField)"
					:modelValue="config.error_title"
					@update:modelValue="(val) => update_config_key('error_title', val)"
				/>
			</div>

			<div class="form-group mb-3">
				<ControlFactory
					:df="with_read_only(errorCodeField)"
					:modelValue="config.error_code"
					@update:modelValue="(val) => update_config_key('error_code', val)"
				/>
			</div>

			<div class="form-group mb-3">
				<TextGeneratorControl
					:df="with_read_only(textGeneratorField)"
					:modelValue="config.text_generator_ui"
					:read_only="readOnly"
					:variableOptions="variable_options"
					@update:modelValue="update_template_ui"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import TextGeneratorControl from "../../../controls/TextGeneratorControl.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { getDerivedFieldState, getFieldLabel } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { config, variable_options, with_read_only, sync_config, update_action_field, store } =
	useActionConfig(props);

const errorTypeField = {
	fieldname: "error_type",
	fieldtype: "Select",
	label: __("Error Type"),
	options: "\nValidation Error\nPermission Error",
	default: "Validation Error",
	description: __("Choose what type of exception should be raised."),
};

const errorTitleField = {
	fieldname: "error_title",
	fieldtype: "Data",
	label: __("Error Title"),
	description: __("Optional dialog title when using Validation Error."),
};

const errorCodeField = {
	fieldname: "error_code",
	fieldtype: "Data",
	label: __("Error Code"),
	description: __("Optional stable code prefix for troubleshooting."),
};

const fieldContext = computed(() => ({
	operation: props.node?.data?.operation,
	processName: props.node?.data?.process_name,
}));

const valueTemplateState = computed(() =>
	getDerivedFieldState(
		props.node?.data?.action_type || "Raise Error",
		"value_template",
		props.node?.data || {},
		store.rule_doc || {},
		fieldContext.value
	)
);

const textGeneratorField = computed(() => ({
	fieldname: "text_generator_ui",
	fieldtype: "Text Generator",
	label:
		getFieldLabel(props.node?.data?.action_type || "Raise Error", "value_template", fieldContext.value) ||
		__("Error Message Builder"),
	reqd: valueTemplateState.value.reqd ? 1 : 0,
}));

function update_template_ui(value) {
	config.text_generator_ui = value;
	const knownVarRoots = (variable_options.value || [])
		.map((v) => String(v?.value || ""))
		.filter((p) => p.startsWith("vars."))
		.map((p) => p.slice(5).split(".")[0]);
	const jinja = compileSegmentsToJinja(value?.segments || [], { knownVarRoots });
	update_action_field("value_template", jinja);
	sync_local_config();
}

function update_config_key(key, value) {
	config[key] = value;
	sync_local_config();
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

	if (!parsed.text_generator_ui && props.node?.data?.value_template) {
		parsed.text_generator_ui = {
			version: 2,
			segments: [{ type: "text", content: props.node.data.value_template }],
		};
	}
	if (!parsed.error_type) {
		parsed.error_type = "Validation Error";
	}

	const current_str = JSON.stringify(config);
	const next_str = JSON.stringify(parsed);
	if (current_str === next_str) return;

	Object.keys(config).forEach((key) => delete config[key]);
	Object.assign(config, parsed);
}

function sync_local_config() {
	const new_config = {};
	Object.entries(config).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== "") {
			new_config[key] = value;
		}
	});
	sync_config(new_config);
}

watch(
	() => props.node?.data?.config,
	(val) => {
		load_local_config(val);
	},
	{ immediate: true, deep: true }
);

function validate() {
	const errors = [];
	const ui = config.text_generator_ui;
	if (valueTemplateState.value.reqd && (!ui || !Array.isArray(ui.segments) || !ui.segments.length)) {
		errors.push(__("Error message is required"));
	}
	if (valueTemplateState.value.reqd && !props.node?.data?.value_template) {
		errors.push(__("Error message template is required"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.raise-error-config {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.section-card {
	border: 1px solid var(--border-color);
	border-radius: 8px;
	padding: 16px;
	background: var(--bg-light, #fff);
}
</style>
