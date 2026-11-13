# 🚀 FEATURE PROPOSAL: Modernized Rule Action Config Modal
- **Target Component**: FlexiRule Action Configuration Modal (`RuleActionModal.vue` / Vue 3 / Frappe UI)
- **Status**: Proposed Architecture & UI Blueprint
- **Author**: FlexiRule UX/UI & Architectural Panel ("The Maestro" & War Room Team)
- **Date**: May 2024

---

## 1. Executive Summary & Core Vision

The legacy FlexiRule Action Configuration Modal suffers from several critical usability bottlenecks: excessive cognitive load, dense three-panel vertical scrolling, hidden mandatory fields, and state desynchronization when switching between action types. Users are presented with multi-column configurations where input fields, operational parameters, and mutation/output specs compete simultaneously for visual attention, regardless of whether prior prerequisites (such as selecting a target DocType or API endpoint) have been established.

This proposal introduces a **Smart Progressive Disclosure Stepper with Adaptive Field Context (The "Intent-First" Model)** for `RuleActionModal.vue`. Instead of dumping input, configuration, and output panels onto the user at once, the redesign transforms action configuration into a clean 4-stage guided flow:

1. **Selection & Intent**: Visual card-based taxonomy selection for action types with instant smart defaults.
2. **Core Target Definition**: Mandatory primary target identification (e.g. Target DocType, Custom Script Name, API Endpoint) establishing the downstream schema.
3. **Parameter Configuration (Progressive Disclosure)**: Dynamically rendered secondary parameters, mapping tables, and conditional fields based on the resolved primary context.
4. **Validation, Output Mapping & Dry-Run Preview**: Variable return bindings, real-time expression validation, and instant dry-run payload preview before committing to canvas.

---

## 2. User Journey & Step-by-Step Flow ("What Comes First")

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ Stage 1: Action Intent      Stage 2: Target Focus    Stage 3: Parameters    Stage 4: Output & Test │
 │  ┌─────────────────┐        ┌─────────────────┐       ┌────────────────┐    ┌────────────────────┐ │
 │  │ ⚡ Document      │  ───►  │ DocType: Lead   │ ───►  │ Field Mappings │───►│ Return Var: lead_id│ │
 │  │ 📜 Custom Script │        │ Action: Update  │       │ Status -> Open │    │ Expression Validation│ │
 │  └─────────────────┘        └─────────────────┘       └────────────────┘    └────────────────────┘ │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

### Cognitive Sequence:
1. **Selection & Intent**: The user opens the modal or drops a new node. Instead of an unconfigured blank form, they are greeted with clear, categorized visual cards (e.g., *Document Action*, *Custom Script*, *API / Webhook*, *Notification*, *Logic Flow*).
2. **Core Target Definition**: Once selected, the UI focuses strictly on the **Primary Anchor Field**. For instance, selecting "Set Field Value / Document Action" immediately prompts for `Target DocType` and `Action Type (Create / Update / Delete)`. All non-essential fields remain hidden or muted until this primary anchor is valid.
3. **Parameter Configuration (Progressive Disclosure)**: Once the primary anchor is resolved, downstream dynamic schemas load asynchronously (e.g., DocType field schemas, API payload templates, or Jinja tokens). Fields are grouped logically into collapsible sections with smart defaults pre-populated.
4. **Validation & Preview**: The final phase exposes return variable assignment (`writes_vars`), output schema contract checks, and a live JSON/dry-run preview panel to verify inputs before clicking **Save & Commit**.

---

## 3. Mandatory Action Fields & Field Hierarchy Matrix

| Action Type | Primary Field (Shown First) | Secondary Fields (Conditional / Progressive) | Smart Defaults / Helper UI |
| :--- | :--- | :--- | :--- |
| **Set Field Value / Document Action** | `Target DocType` & `Document Operation` (Create, Update, Delete) | `Reference DocName Expression`, `Field Value Mappings`, `Child Table Updates` | Auto-detects field types (Link, Select, Check, Dates) with `FlexValueControl` auto-completion |
| **Execute Custom Script / Process** | `Process Handler / Custom Script` | `Input Context Variables`, `Timeout (ms)`, `Execution Mode (Async/Sync)` | Syntax-highlighted code drawer, dynamic variable injection tokens |
| **Trigger API / Webhook** | `Endpoint URL` & `HTTP Method` (GET, POST, PUT, DELETE) | `Headers Dict`, `Body Payload Mapping`, `Auth Profile`, `Retry Policy` | Pre-built OAuth2/API Key header presets, JSON payload formatter & validator |
| **Send Notification** | `Channel` (Email, System Notification, Slack/Webhook) & `Recipient Group` | `Template ID / Subject`, `Message Body`, `Attachment Rules`, `Dynamic Tokens` | Interactive Jinja token picker dropdown with live context evaluation |
| **Query Records / Fetch** | `Source DocType` & `Filter Criteria` | `Fields to Fetch`, `Sort Order`, `Limit / Offset`, `Child Table Aggregations` | Visual Query Builder with nested logic (`AND`/`OR`) and automatic limit guardrails |
| **Sub-Rule / Workflow Flow** | `Target Sub-Rule` | `Input Contract Mappings`, `Failure Strategy`, `Version Lock` | Dynamic mapping matrix linking parent context variables to child input contract |

---

## 4. UI/UX Architecture & Component Layout

### Layout Paradigm: Hybrid Adaptive Split-Panel Wizard
- **Header**:
  - Breadcrumb navigation (`Rule Name` > `Action Node ID` > `Action Type`).
  - Progress Stepper Indicator (1. Intent -> 2. Target -> 3. Configuration -> 4. Output & Test).
  - Dirty indicator badge with cross-step change counter.
  - Global Keyboard Shortcuts indicator (`Ctrl+S` Save, `Esc` Cancel, `Alt+1..4` Jump to Step).
- **Left Panel (Guided Wizard / Navigation & Context)**:
  - Vertical step progression bar with real-time validation badges (Green check for valid steps, Amber warning for missing required fields).
  - Quick Variable Palette: Draggable / clickable contextual variables available in current scope (`rule_input`, prior step outputs).
- **Center Panel (Primary Workstation)**:
  - Focused form viewport rendering only active step fields to prevent visual overload.
  - Smart field layout with single-column primary fields and dual-column secondary parameter grids.
  - Native Frappe UI integration with Tailwind micro-typography and dark-mode compatibility.
- **Right Panel (Live Dynamic Inspector & Preview)**:
  - Collapsible drawer showing:
    1. **Contract Inspector**: Active action schema requirements.
    2. **Expression Test Sandbox**: Real-time evaluation of Jinja / FlexValue expressions against sample context.
    3. **Generated Payload / Code Preview**: Raw JSON structure passed to backend handler.

---

## 5. Technical Implementation Blueprint (Vue 3 / Frappe)

### Component Architecture Breakdown
```
flexirule/public/js/flexirule/rule_builder/components/rule_config/
├── RuleActionModal.vue            # Top-level modal container, step management, focus trap & keyboard navigation
├── steps/
│   ├── Step1IntentSelection.vue   # Visual action type selection grid with search & category filters
│   ├── Step2TargetDefinition.vue  # Anchor target resolution (DocType, Script, Endpoint)
│   ├── Step3ParameterConfig.vue   # Progressive field layout rendering dynamic action-specific controls
│   └── Step4OutputValidation.vue  # Output variable assignment, schema validation & dry-run tester
├── common/
│   ├── ActionStepProgress.vue     # Step header & status indicator component
│   ├── ActionContextInspector.vue # Side drawer for available context variables & payload preview
│   └── DynamicFieldRenderer.vue   # Reactive schema-driven control wrapper integrating FlexValueControl
└── composables/
    ├── useActionModalWizard.js    # Wizard state, step validation logic & keyboard navigation
    └── useActionSchemaResolver.js # Asynchronous dynamic field schema generation based on target
```

### Vue 3 Composition API Implementation Sample (`useActionModalWizard.js`)

```javascript
import { ref, computed, reactive, watch } from 'vue';
import { useRuleStore, useMetaStore } from '../../stores';
import { getContract } from '../../../core/contracts';

export function useActionModalWizard(props, emit) {
    const currentStep = ref(1);
    const totalSteps = 4;
    const ruleStore = useRuleStore();
    const metaStore = useMetaStore();

    const wizardState = reactive({
        actionType: props.node?.data?.action_type || '',
        targetDoctype: props.node?.data?.config?.doctype || '',
        config: { ...props.node?.data?.config },
        returnVariable: props.node?.data?.return_variable || '',
        stepValidation: {
            1: false,
            2: false,
            3: false,
            4: false,
        }
    });

    // Step 1 Validation: Action type selected
    const isStep1Valid = computed(() => !!wizardState.actionType);

    // Step 2 Validation: Primary target specified based on contract
    const isStep2Valid = computed(() => {
        const contract = getContract(wizardState.actionType);
        if (!contract) return false;
        if (contract.requires_doctype && !wizardState.targetDoctype) return false;
        if (contract.requires_endpoint && !wizardState.config.endpoint_url) return false;
        return true;
    });

    function goToStep(step) {
        if (step < currentStep.value || canNavigateTo(step)) {
            currentStep.value = step;
        }
    }

    function canNavigateTo(step) {
        if (step === 2) return isStep1Valid.value;
        if (step === 3) return isStep1Valid.value && isStep2Valid.value;
        if (step === 4) return isStep1Valid.value && isStep2Valid.value;
        return false;
    }

    return {
        currentStep,
        totalSteps,
        wizardState,
        isStep1Valid,
        isStep2Valid,
        goToStep,
        canNavigateTo
    };
}
```

### Migration & Backward Compatibility
- Existing nodes stored in JSON continue to deserialize seamlessly; `useActionConfig.js` automatically populates `wizardState` from existing `node.data`.
- The legacy raw JSON configuration view (`viewMode = 'raw'`) is preserved via a dedicated header toggle button (`Ctrl+Alt+2`) for power users who require direct key-value manipulation.
