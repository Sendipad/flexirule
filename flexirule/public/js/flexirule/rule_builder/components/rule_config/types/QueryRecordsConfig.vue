<template>
	<div class="query-records-config">
		<div v-if="!node.data?.operation" class="empty-mode-state">
			<i class="fa fa-database opacity-20 mb-3" style="font-size: 32px"></i>
			<p class="text-muted">
				{{ __("Please select a Query Mode in the Setup panel to proceed.") }}
			</p>
		</div>

		<template v-else>
			<div class="fxr-stack fxr-stack--gap-4">
				<!-- Query Definition -->
				<div class="fxr-card">
					<div class="fxr-card-header">
						<span class="fxr-label-sm">{{ __("Query Definition") }}</span>
					</div>
					<div class="fxr-card-body fxr-stack fxr-stack--gap-4">
						<div v-if="isDocMode">
							<ControlFactory
								:df="docnameField"
								:modelValue="node.data.reference_docname"
								@update:modelValue="onUpdate('reference_docname', $event)"
							/>
						</div>

						<div v-if="isListMode">
							<div class="fxr-label">{{ __("Filters") }}</div>
							<div class="filter-builder-wrapper">
								<ConditionBuilder
									:modelValue="config.filters"
									:docFields="sourceFields"
									:variableOptions="variable_options"
									@update:modelValue="onUpdateConfig('filters', $event)"
								/>
							</div>
						</div>

						<div v-if="isReportMode">
							<ControlFactory
								:df="reportNameField"
								:modelValue="node.data.reference_docname"
								@update:modelValue="onUpdate('reference_docname', $event)"
							/>
							<div class="mt-4" v-if="node.data.reference_docname">
								<div class="fxr-label-sm mb-3">{{ __("Report Parameters") }}</div>
								<FlexiGrid
									:df="reportParamsDf"
									:modelValue="config.report_params"
									@update:modelValue="onUpdateConfig('report_params', $event)"
								/>
							</div>
						</div>
					</div>
				</div>

				<!-- Result Settings -->
				<div class="fxr-card" v-if="isListMode || isReportMode">
					<div class="fxr-card-header">
						<span class="fxr-label-sm">{{ __("Result Settings") }}</span>
					</div>
					<div class="fxr-card-body fxr-stack fxr-stack--gap-4">
						<div class="fxr-row fxr-row--gap-4">
							<div class="flex-1">
								<ControlFactory
									:df="limitField"
									:modelValue="config.limit"
									@update:modelValue="onUpdateConfig('limit', $event)"
								/>
							</div>
							<div class="flex-1">
								<ControlFactory
									:df="orderField"
									:modelValue="config.order_by"
									@update:modelValue="onUpdateConfig('order_by', $event)"
								/>
							</div>
						</div>
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
import ConditionBuilder from "../../condition_builder/ConditionBuilder.vue";
import FlexiGrid from "../../../controls/FlexiGrid.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { config, variable_options, update_action_field, store } = useActionConfig(props);

const isDocMode = computed(() => props.node.data?.operation === "Query Doc");
const isListMode = computed(() => props.node.data?.operation === "Query List");
const isReportMode = computed(() => props.node.data?.operation === "Query Report");

const sourceFields = ref([]);

const docnameField = {
	fieldname: "reference_docname",
	fieldtype: "Data",
	label: __("Document Name"),
	description: __("The name of the document to query (e.g. INV-2024-001)"),
};

const reportNameField = {
	fieldname: "reference_docname",
	fieldtype: "Link",
	label: __("Report"),
	options: "Report",
};

const limitField = {
	fieldname: "limit",
	fieldtype: "Int",
	label: __("Result Limit"),
};

const orderField = {
	fieldname: "order_by",
	fieldtype: "Data",
	label: __("Order By"),
	placeholder: "creation desc",
};

const reportParamsDf = {
	fieldname: "report_params",
	fieldtype: "Table",
	label: __("Parameters"),
	fields: [
		{ fieldname: "parameter", label: __("Parameter"), fieldtype: "Data", in_list_view: 1 },
		{ fieldname: "value", label: __("Value"), fieldtype: "Data", in_list_view: 1 },
	],
};

function onUpdate(fieldname, value) {
	update_action_field(fieldname, value);
}

function onUpdateConfig(key, value) {
	config[key] = value;
	update_action_field("config", JSON.stringify(config));
}

onMounted(async () => {
	const doctype = props.node.data?.reference_doctype;
	if (doctype) {
		sourceFields.value = await flexirule.utils.get_doctype_fields(doctype);
	}
});

watch(
	() => props.node.data?.reference_doctype,
	async (newVal) => {
		if (newVal) {
			sourceFields.value = await flexirule.utils.get_doctype_fields(newVal);
		}
	}
);
</script>

<style scoped>
.query-records-config {
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

.filter-builder-wrapper {
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	padding: 12px;
	background: var(--fr-bg-muted);
}

.fxr-label {
	font-size: var(--fr-text-sm);
	font-weight: 500;
	color: var(--fr-text-secondary);
	margin-bottom: 8px;
}

.flex-1 {
	flex: 1;
}
</style>
