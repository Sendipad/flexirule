<template>
	<div class="loop-config">
		<div class="fxr-stack fxr-stack--gap-4">
			<div class="fxr-card">
				<div class="fxr-card-header">
					<span class="fxr-label-sm">{{ __("Loop Source") }}</span>
				</div>
				<div class="fxr-card-body fxr-stack fxr-stack--gap-4">
					<ControlFactory
						:df="loopTypeField"
						:modelValue="config.loop_type || 'Items'"
						@update:modelValue="updateConfig('loop_type', $event)"
					/>

					<div v-if="config.loop_type === 'Items'">
						<ControlFactory
							:df="itemsField"
							:modelValue="config.items_source"
							@update:modelValue="updateConfig('items_source', $event)"
						/>
					</div>

					<div v-if="config.loop_type === 'Range'">
						<div class="fxr-row fxr-row--gap-4">
							<div class="flex-1">
								<ControlFactory
									:df="startField"
									:modelValue="config.range_start"
									@update:modelValue="updateConfig('range_start', $event)"
								/>
							</div>
							<div class="flex-1">
								<ControlFactory
									:df="endField"
									:modelValue="config.range_end"
									@update:modelValue="updateConfig('range_end', $event)"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="fxr-card">
				<div class="fxr-card-header">
					<span class="fxr-label-sm">{{ __("Iteration Details") }}</span>
				</div>
				<div class="fxr-card-body fxr-stack fxr-stack--gap-4">
					<ControlFactory
						:df="iteratorNameField"
						:modelValue="node.data.iterator_name"
						@update:modelValue="update_action_field('iterator_name', $event)"
					/>
					<ControlFactory
						v-if="config.loop_type === 'Items'"
						:df="indexNameField"
						:modelValue="config.index_name"
						@update:modelValue="updateConfig('index_name', $event)"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useActionConfig } from "../../../composables/useActionConfig";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
});

const { config, update_action_field } = useActionConfig(props);

const loopTypeField = {
	fieldname: "loop_type",
	fieldtype: "Select",
	label: __("Loop Type"),
	options: "Items\nRange",
};

const itemsField = {
	fieldname: "items_source",
	fieldtype: "Data",
	label: __("Items to Iterate"),
	description: __("A list, child table name, or expression."),
};

const startField = {
	fieldname: "range_start",
	fieldtype: "Int",
	label: __("Start"),
};

const endField = {
	fieldname: "range_end",
	fieldtype: "Int",
	label: __("End"),
};

const iteratorNameField = {
	fieldname: "iterator_name",
	fieldtype: "Data",
	label: __("Item Variable Name"),
	description: __("The name of the variable representing the current item."),
};

const indexNameField = {
	fieldname: "index_name",
	fieldtype: "Data",
	label: __("Index Variable Name"),
	description: __("Optional name for the loop index (0, 1, 2...)."),
};

function updateConfig(key, value) {
	config[key] = value;
	update_action_field("config", JSON.stringify(config));
}
</script>

<style scoped>
.loop-config {
	display: flex;
	flex-direction: column;
}

.flex-1 {
	flex: 1;
}
</style>
