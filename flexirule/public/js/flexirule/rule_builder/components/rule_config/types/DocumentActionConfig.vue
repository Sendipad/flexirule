<template>
	<div class="document-action-config">
		<div v-if="!node.data?.operation" class="empty-mode-state">
			<i class="fa fa-file-text-o opacity-20 mb-3" style="font-size: 32px"></i>
			<p class="text-muted">
				{{ __("Please select an Action in the Setup panel to proceed.") }}
			</p>
		</div>

		<template v-else>
			<div class="fxr-stack fxr-stack--gap-4">
				<div class="fxr-card">
					<div class="fxr-card-header">
						<span class="fxr-label-sm">{{ __("Document Context") }}</span>
					</div>
					<div class="fxr-card-body fxr-stack fxr-stack--gap-4">
						<div v-if="requiresDocname">
							<ControlFactory
								:df="docnameField"
								:modelValue="node.data.reference_docname"
								@update:modelValue="
									update_action_field('reference_docname', $event)
								"
							/>
						</div>

						<div v-if="is_create_new">
							<ControlFactory
								:df="creationModeField"
								:modelValue="config.creation_mode"
								@update:modelValue="updateConfig('creation_mode', $event)"
							/>
						</div>

						<div v-if="is_workflow_action">
							<ControlFactory
								:df="workflowActionField"
								:modelValue="config.workflow_action"
								@update:modelValue="updateConfig('workflow_action', $event)"
							/>
						</div>
					</div>
				</div>

				<div class="fxr-card">
					<div class="fxr-card-header">
						<span class="fxr-label-sm">{{ __("Data Mapping") }}</span>
					</div>
					<div class="fxr-card-body">
						<FlexiGrid
							:df="mappingDf"
							:modelValue="config.mappings"
							@update:modelValue="updateConfig('mappings', $event)"
						/>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, watch, ref, onMounted } from "vue";
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";
import FlexiGrid from "../../../controls/FlexiGrid.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { config, variable_options, update_action_field, store } = useActionConfig(props);

const is_create_new = computed(() => props.node.data?.operation === "Create New");
const is_workflow_action = computed(() => props.node.data?.operation === "Workflow Action");
const requiresDocname = computed(() =>
	["Update Existing", "Delete Record", "Submit Record", "Workflow Action"].includes(
		props.node.data?.operation
	)
);

const docnameField = {
	fieldname: "reference_docname",
	fieldtype: "Data",
	label: __("Document Name"),
	description: __("The name of the document (e.g. INV-2024-001)"),
};

const creationModeField = {
	fieldname: "creation_mode",
	fieldtype: "Select",
	label: __("Creation Mode"),
	options: "Always Create\nUpdate if Exists",
};

const workflowActionField = {
	fieldname: "workflow_action",
	fieldtype: "Data",
	label: __("Workflow Action"),
	placeholder: "Approve / Reject / Submit",
};

const targetFields = ref([]);

const mappingDf = computed(() => ({
	fieldname: "mappings",
	fieldtype: "Table",
	label: __("Field Mappings"),
	fields: [
		{
			fieldname: "fieldname",
			label: __("Target Field"),
			fieldtype: "Select",
			options: targetFields.value,
			in_list_view: 1,
		},
		{
			fieldname: "value",
			label: __("Value Expression"),
			fieldtype: "Data",
			in_list_view: 1,
		},
	],
}));

function updateConfig(key, value) {
	config[key] = value;
	update_action_field("config", JSON.stringify(config));
}

onMounted(async () => {
	const doctype = props.node.data?.reference_doctype;
	if (doctype) {
		const fields = await flexirule.utils.get_doctype_fields(doctype);
		targetFields.value = fields.map((f) => ({ label: f.label, value: f.fieldname }));
	}
});

watch(
	() => props.node.data?.reference_doctype,
	async (newVal) => {
		if (newVal) {
			const fields = await flexirule.utils.get_doctype_fields(newVal);
			targetFields.value = fields.map((f) => ({ label: f.label, value: f.fieldname }));
		}
	}
);
</script>

<style scoped>
.document-action-config {
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
