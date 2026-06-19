<template>
	<div class="notify-config">
		<div v-if="!props.node?.data?.operation" class="empty-mode-state text-center p-5">
			<i class="fa fa-bell fa-3x text-muted mb-3 opacity-20"></i>
			<p class="text-muted">
				{{ __("Please select a Notification Type in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container">
			<div class="config-section section-card">
				<div v-if="is_email" class="form-group mb-3">
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(subjectField)"
						:modelValue="config.subject"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('subject', val)"
					/>
				</div>

				<div v-if="is_email" class="form-group mb-3">
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(recipientsField)"
						:modelValue="config.recipients"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('recipients', val)"
					/>
				</div>

				<div v-if="is_system_notification" class="form-group mb-3">
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(subjectField)"
						:modelValue="config.subject"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('subject', val)"
					/>
				</div>

				<div v-if="is_system_notification" class="form-group mb-3">
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(forUserField)"
						:modelValue="config.for_user"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('for_user', val)"
					/>
				</div>

				<div v-if="is_provider" class="form-group mb-3">
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(providerField)"
						:modelValue="config.provider"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('provider', val)"
					/>
				</div>

				<div v-if="is_provider" class="form-group mb-3">
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(recipientField)"
						:modelValue="config.recipient"
						:showValidation="showValidation"
						@update:modelValue="(val) => update_config_key('recipient', val)"
					/>
				</div>

				<div class="form-group mb-3">
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(textGeneratorField)"
						:modelValue="config.text_generator_ui"
						:showValidation="showValidation"
						@update:modelValue="update_template_ui"
					/>
				</div>

				<div v-if="is_email" class="form-group mb-3">
					<label class="form-label">{{ __("Attach Document PDF") }}</label>
					<ControlFactory
						:ref="setControlRef"
						:df="with_read_only(attachDocField)"
						:modelValue="config.attach_doc"
						@update:modelValue="(val) => update_config_key('attach_doc', val)"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch, ref, onBeforeUpdate } from "vue";
import { fromCodeString } from "../../../utils/serialization";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import TextGeneratorControl from "../../../controls/TextGeneratorControl.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { getContract, getEffectiveActionPolicy } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const showValidation = ref(false);
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

const { config, variable_options, with_read_only, sync_config, update_action_field } =
	useActionConfig(props);

const EMAIL_MODE = "Email";
const SYSTEM_NOTIFICATION_MODE = "System Notification";
const PROVIDER_MODE = "Provider";

const subjectField = computed(() => ({
	fieldname: "subject",
	fieldtype: "Data",
	label: __("Subject"),
	reqd: isConfigKeyRequired("subject") ? 1 : 0,
}));

const recipientsField = computed(() => ({
	fieldname: "recipients",
	fieldtype: "Small Text",
	label: __("Recipients"),
	reqd: isConfigKeyRequired("recipients") ? 1 : 0,
	description: __("One email per line, comma-separated values, or a Jinja template."),
}));

const forUserField = {
	fieldname: "for_user",
	fieldtype: "Link",
	label: __("For User"),
	options: "User",
};

const attachDocField = {
	fieldname: "attach_doc",
	fieldtype: "Check",
	label: __("Attach Document PDF"),
};

const providerField = computed(() => ({
	fieldname: "provider",
	fieldtype: "Data",
	label: __("Provider"),
	reqd: isConfigKeyRequired("provider") ? 1 : 0,
}));

const recipientField = computed(() => ({
	fieldname: "recipient",
	fieldtype: "Data",
	label: __("Recipient"),
	reqd: isConfigKeyRequired("recipient") ? 1 : 0,
}));

const textGeneratorField = computed(() => ({
	fieldname: "text_generator_ui",
	fieldtype: "Text Generator",
	label: __("Message Builder"),
	reqd: (getContract(props.node?.data?.action_type || "Notify").required_fields || []).includes(
		"value_template"
	)
		? 1
		: 0,
}));

const notify_mode = computed(() => props.node?.data?.operation || "");
const context = computed(() => ({ operation: notify_mode.value }));
const operationPolicy = computed(() =>
	getEffectiveActionPolicy(props.node?.data?.action_type || "Notify", context.value)
);
const requiredConfigKeys = computed(() => operationPolicy.value?.required_config_keys || []);
const is_email = computed(() => notify_mode.value === EMAIL_MODE);
const is_system_notification = computed(() => notify_mode.value === SYSTEM_NOTIFICATION_MODE);
const is_provider = computed(() => notify_mode.value === PROVIDER_MODE);

function isConfigKeyRequired(key) {
	return requiredConfigKeys.value.includes(key);
}

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
	const parsed = typeof val === "string" ? fromCodeString(val) : val || {};

	// Backwards compat: value_template
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
	const new_config = {};
	Object.entries(config).forEach(([key, value]) => {
		if (value !== undefined && value !== null && value !== "") {
			new_config[key] = value;
		}
	});

	// sync_config in useActionConfig already performs a string compare against props.node.data.config
	sync_config(new_config);
}

watch(
	() => props.node?.data?.config,
	(val) => {
		load_local_config(val);
	},
	{ immediate: true, deep: true }
);

async function validate() {
	showValidation.value = true;
	const errors = [];

	// 1. Core Control Validation (Aggregated)
	const results = await Promise.all(
		(controlRefs.value || []).map((ctrl) => {
			if (ctrl && typeof ctrl.validate === "function") {
				return ctrl.validate();
			}
			return { valid: true };
		})
	);
	results.forEach((res) => {
		if (!res.valid && res.errors) errors.push(...res.errors);
	});

	// 2. Logic-based Validation
	if (!props.node?.data?.value_template) {
		errors.push(__("Message content is required"));
	}

	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.notify-config {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.section-card {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 8px;
	padding: 16px;
	background-color: var(--fxr-bg-card);
}

.form-label {
	font-weight: 500;
	margin-bottom: 6px;
	display: block;
	font-size: 13px;
}
</style>
