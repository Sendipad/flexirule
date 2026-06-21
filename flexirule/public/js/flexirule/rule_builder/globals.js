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
import MultiSelectList from "./controls/MultiSelectList.vue";
import ComboBoxControl from "./controls/ComboBoxControl.vue";
import InlineTableControl from "./controls/InlineTableControl.vue";
import FlexiGrid from "./controls/FlexiGrid.vue";
import PercentSliderControl from "./controls/PercentSliderControl.vue";
import FlexValueControl from "./controls/FlexValueControl.vue";
import TextGeneratorControl from "./controls/TextGeneratorControl.vue";
import TimePickerControl from "./controls/TimePickerControl.vue";
import ResourceMapperControl from "./controls/ResourceMapperControl.vue";
import CollapsibleSection from "./controls/CollapsibleSection.vue";

import { fieldRevealDirective } from "./utils/directives.js";

export function registerGlobalComponents(app) {
	app.directive("fxr-fieldname", fieldRevealDirective);

	app.component("ComboBoxControl", ComboBoxControl)
		.component("FlexiGrid", FlexiGrid)
		.component("DataControl", DataControl)
		.component("SelectControl", SelectControl)
		.component("CheckControl", CheckControl)
		.component("TextControl", TextControl)
		.component("CodeControl", CodeControl)
		.component("InlineTableControl", InlineTableControl)
		.component("MultiSelectList", MultiSelectList)
		.component("PercentSliderControl", PercentSliderControl)
		.component("FlexValueControl", FlexValueControl)
		.component("TextGeneratorControl", TextGeneratorControl)
		.component("TimePickerControl", TimePickerControl)
		.component("ResourceMapperControl", ResourceMapperControl)
		.component("CollapsibleSection", CollapsibleSection);

	app.config.globalProperties.__ = window.__ || ((s) => s);
}
