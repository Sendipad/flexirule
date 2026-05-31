import "./flexirule/utils/utils.js";
import "./flexirule/utils/variable_validator.js";
import "./flexirule/utils/patches.js";
import "./flexirule/core/ProcessConfigurator.js";
import * as contracts from "./flexirule/core/contracts.js";

frappe.provide("flexirule");
flexirule.contracts = contracts;
