import LinkControl from "./controls/LinkControl.vue";
import DataControl from "./controls/DataControl.vue";
import SelectControl from "./controls/SelectControl.vue";
import CheckControl from "./controls/CheckControl.vue";
import TextControl from "./controls/TextControl.vue";
import CodeControl from "./controls/CodeControl.vue";
import MultiCheckControl from "./controls/MultiCheckControl.vue";
import AutocompleteControl from "./controls/AutocompleteControl.vue";
import FieldPickerControl from "./controls/FieldPickerControl.vue";
import InlineTableControl from "./controls/InlineTableControl.vue";
import MultiFieldPickerControl from "./controls/MultiFieldPickerControl.vue";
import MultiSelectControl from "./controls/MultiSelectControl.vue";
import PercentSliderControl from "./controls/PercentSliderControl.vue";

export function registerGlobalComponents(app) {
	app.component("LinkControl", LinkControl)
		.component("DataControl", DataControl)
		.component("SelectControl", SelectControl)
		.component("CheckControl", CheckControl)
		.component("TextControl", TextControl)
		.component("CodeControl", CodeControl)
		.component("MultiCheckControl", MultiCheckControl)
		.component("AutocompleteControl", AutocompleteControl)
		.component("FieldPickerControl", FieldPickerControl)
		.component("InlineTableControl", InlineTableControl)
		.component("MultiFieldPickerControl", MultiFieldPickerControl)
		.component("MultiSelectControl", MultiSelectControl)
		.component("PercentSliderControl", PercentSliderControl);

	app.config.globalProperties.__ = window.__ || ((s) => s);
}
