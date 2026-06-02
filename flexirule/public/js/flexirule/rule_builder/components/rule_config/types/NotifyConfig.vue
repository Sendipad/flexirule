<template>
	<div class="notify-config">
		<div v-if="!props.node?.data?.operation" class="empty-mode-state">
			<i class="fa fa-bell opacity-20 mb-3" style="font-size: 32px"></i>
			<p class="text-muted">
				{{ __("Please select a Notification Type in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container">
			<div class="fxr-stack fxr-stack--gap-4">
				<div class="fxr-card">
					<div class="fxr-card-header">
						<span class="fxr-label-sm">{{ __("Notification Details") }}</span>
					</div>
					<div class="fxr-card-body fxr-stack fxr-stack--gap-4">
						<div v-if="is_email || is_system_notification">
							<ControlFactory
								:df="with_read_only(subjectField)"
								:modelValue="config.subject"
								@update:modelValue="(val) => update_config_key('subject', val)"
							/>
						</div>

						<div v-if="is_email">
							<ControlFactory
								:df="with_read_only(recipientsField)"
								:modelValue="config.recipients"
								@update:modelValue="(val) => update_config_key('recipients', val)"
							/>
						</div>

						<div v-if="is_system_notification">
							<ControlFactory
								:df="with_read_only(forUserField)"
								:modelValue="config.for_user"
								@update:modelValue="(val) => update_config_key('for_user', val)"
							/>
						</div>

						<div v-if="is_provider">
							<ControlFactory
								:df="with_read_only(providerField)"
								:modelValue="config.provider"
								@update:modelValue="(val) => update_config_key('provider', val)"
							/>
						</div>

						<div v-if="is_provider">
							<ControlFactory
								:df="with_read_only(recipientField)"
								:modelValue="config.recipient"
								@update:modelValue="(val) => update_config_key('recipient', val)"
							/>
						</div>
					</div>
				</div>

				<div class="fxr-card">
					<div class="fxr-card-header">
						<span class="fxr-label-sm">{{ __("Message Content") }}</span>
					</div>
					<div class="fxr-card-body">
						<ControlFactory
							:df="with_read_only(textGeneratorField)"
							:modelValue="config.text_generator_ui"
							@update:modelValue="update_template_ui"
						/>
					</div>
				</div>

				<div v-if="is_email" class="fxr-card">
					<div class="fxr-card-body">
						<ControlFactory
							:df="with_read_only(attachDocField)"
							:modelValue="config.attach_doc"
							@update:modelValue="(val) => update_config_key('attach_doc', val)"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import { compileSegmentsToJinja } from "../../../utils/text_generator";
import { getContract, getEffectiveActionPolicy } from "../../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

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
	if (!ui || !Array.isArray(ui.segments) || !ui.segments.length) {
		errors.push(__("Message Builder content is required"));
	}
	const labels = {
		subject: __("Subject"),
		recipients: __("Recipients"),
		provider: __("Provider"),
		recipient: __("Recipient"),
	};
	for (const key of requiredConfigKeys.value) {
		if (!config[key]) {
			errors.push(__("{0} is required").replace("{0}", labels[key] || key));
		}
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.notify-config {
	display: flex;
	flex-direction: column;
}

.empty-mode-state {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	padding: 60px 20px;
}
</style>
