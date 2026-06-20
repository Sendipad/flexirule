import sys

def fix_action_field_properties():
    path = "flexirule/public/js/flexirule/rule_builder/components/ActionFieldProperties.vue"
    with open(path, "r") as f:
        content = f.read()

    # Target specific block and adjust indentation
    old = """\t\t\t\t\t\toperation: props.nodeData?.operation,
\t\t\t\t\t\tprocessName: props.nodeData?.process_name,
\t\t\t\t\t})"""
    new = """\t\t\t\t\t\toperation: props.nodeData?.operation,
\t\t\t\t\t\tprocessName: props.nodeData?.process_name,
\t\t\t\t\t})"""
    # Wait, Prettier diff said:
    # -					})
    # +				  })
    # It seems it wants it 2 spaces less or something if it's mixed?
    # But .prettierrc says useTabs: true.

    content = content.replace("processName: props.nodeData?.process_name,\n\t\t\t\t  })", "processName: props.nodeData?.process_name,\n\t\t\t\t})")
    # Actually let's just use the diff's hint.
    content = content.replace("processName: props.nodeData?.process_name,\n\t\t\t\t\t})", "processName: props.nodeData?.process_name,\n\t\t\t\t  })")

    with open(path, "w") as f:
        f.write(content)

def fix_rule_config_modal():
    path = "flexirule/public/js/flexirule/rule_builder/components/rule_config/RuleConfigModal.vue"
    with open(path, "r") as f:
        content = f.read()

    content = content.replace("'Expand Input Panel'\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t)", "'Expand Input Panel'\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t  )")
    content = content.replace("'Collapse Input Panel'\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t)", "'Collapse Input Panel'\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t  )")

    with open(path, "w") as f:
        f.write(content)

if __name__ == "__main__":
    fix_action_field_properties()
    fix_rule_config_modal()
