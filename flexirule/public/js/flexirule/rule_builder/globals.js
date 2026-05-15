/**
 * registerGlobalComponents
 *
 * Registers reusable FlexiRule controls as global Vue components so they can
 * be resolved by string name (used in SchemaRenderer, FlexiGrid, etc.).
 *
 * Legacy controls (LinkControl, AutocompleteControl, FieldPickerControl) have
 * been removed — all resolved through ComboBoxControl via ControlFactory.
 */
import DataControl from "./controls/DataControl.vue";
import SelectControl from "./controls/SelectControl.vue";
import CheckControl from "./controls/CheckControl.vue";
import TextControl from "./controls/TextControl.vue";
import CodeControl from "./controls/CodeControl.vue";
import MultiCheckControl from "./controls/MultiCheckControl.vue";
import MultiSelectList from "./controls/MultiSelectList.vue";
import ComboBoxControl from "./controls/ComboBoxControl.vue";
import InlineTableControl from "./controls/InlineTableControl.vue";
import MultiFieldPickerControl from "./controls/MultiFieldPickerControl.vue";
import MultiSelectControl from "./controls/MultiSelectControl.vue";
import PercentSliderControl from "./controls/PercentSliderControl.vue";

export function registerGlobalComponents(app) {
	app.component("ComboBoxControl", ComboBoxControl)
		.component("DataControl", DataControl)
		.component("SelectControl", SelectControl)
		.component("CheckControl", CheckControl)
		.component("TextControl", TextControl)
		.component("CodeControl", CodeControl)
		.component("MultiCheckControl", MultiCheckControl)
		.component("InlineTableControl", InlineTableControl)
		.component("MultiFieldPickerControl", MultiFieldPickerControl)
		.component("MultiSelectControl", MultiSelectControl)
		.component("MultiSelectList", MultiSelectList)
		.component("PercentSliderControl", PercentSliderControl);

	app.config.globalProperties.__ = window.__ || ((s) => s);
}
