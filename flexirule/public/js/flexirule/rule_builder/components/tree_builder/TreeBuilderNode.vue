<script setup>
import {computed,inject,ref} from "vue";
import {isGroupNode,isScopeNode} from "./tree_builder_utils.js";
import TreeBuilderGroup from "./TreeBuilderGroup.vue";
import TreeBuilderScope from "./TreeBuilderScope.vue";
import TreeBuilderLeaf from "./TreeBuilderLeaf.vue";
defineOptions({name:"TreeBuilderNode"});
const props=defineProps({node:{type:Object,required:true},index:{type:Number,required:true},parent:{type:Object,required:true},readOnly:Boolean,allowGroups:Boolean,groupOperators:{type:Array,default:()=>["and","or"]},leafLabel:{type:String,default:__("Condition")},scopeLabel:{type:String,default:__("Scope")},operatorLabel:{type:Function,default:v=>v}});
const emit=defineEmits(["remove","operator"]);
const api=inject("treeBuilderContext",null),dragOver=ref(false);
const kind=computed(()=>props.node.type),children=computed(()=>props.node.children||[]),context=computed(()=>api?.getNodeContext?.(props.node.id)||{scopes:[],path:[]}),scopeTitle=computed(()=>props.node.scope?.label||props.node.scope?.key||props.scopeLabel);
function dragStart(e){if(props.readOnly)return;e.stopPropagation();api?.beginDrag(props.node.id);e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",props.node.id||"");}
function dragOverNode(e){if(props.readOnly||!["group","scope"].includes(kind.value))return;e.preventDefault();e.stopPropagation();dragOver.value=true;}
function dragLeave(){dragOver.value=false}
function drop(e){e.preventDefault();e.stopPropagation();dragOver.value=false;api?.dropNode(props.node.id)}
</script>
<template>
<div class="tree-node" :class="{'drag-over':dragOver}" draggable="true" @dragstart="dragStart" @dragover="dragOverNode" @dragleave="dragLeave" @drop="drop">
<TreeBuilderGroup v-if="isGroupNode(node)" :node="node" :operators="groupOperators" :operatorLabel="operatorLabel" :readOnly="readOnly" :allowGroups="allowGroups" @operator="$emit('operator',$event)" @add-leaf="api?.addLeaf(node.id)" @add-group="api?.addGroup(node.id)" @remove="$emit('remove')">
<template #children><TreeBuilderNode v-for="(child,i) in children" :key="child.id" :node="child" :index="i" :parent="node" :readOnly="readOnly" :allowGroups="allowGroups" :groupOperators="groupOperators" :leafLabel="leafLabel" :scopeLabel="scopeLabel" :operatorLabel="operatorLabel" @remove="api?.removeNode(child.id)" @operator="api?.setOperator(child.id,$event)"><template #default="p"><slot v-bind="p"/></template></TreeBuilderNode></template>
</TreeBuilderGroup>
<TreeBuilderScope v-else-if="isScopeNode(node)" :node="node" :label="scopeTitle" :scopeLabel="node.scope?.key && node.scope?.label ? node.scope.key : ''" :readOnly="readOnly" :allowGroups="allowGroups" @add-leaf="api?.addLeaf(node.id)" @add-group="api?.addGroup(node.id)" @remove="$emit('remove')">
<template #children><TreeBuilderNode v-for="(child,i) in children" :key="child.id" :node="child" :index="i" :parent="node" :readOnly="readOnly" :allowGroups="allowGroups" :groupOperators="groupOperators" :leafLabel="leafLabel" :scopeLabel="scopeLabel" :operatorLabel="operatorLabel" @remove="api?.removeNode(child.id)" @operator="api?.setOperator(child.id,$event)"><template #default="p"><slot v-bind="p"/></template></TreeBuilderNode></template>
</TreeBuilderScope>
<TreeBuilderLeaf v-else :node="node" :context="context" :index="index" :parent="parent" :readOnly="readOnly" @remove="$emit('remove')"><template #default="p"><slot v-bind="p"/></template></TreeBuilderLeaf>
</div>
</template>
<style scoped>.tree-node{min-width:0}.tree-node.drag-over{background:var(--fxr-node-accent-light,var(--fxr-accent-soft));border-radius:var(--fxr-radius-lg);box-shadow:inset 0 0 0 2px var(--fxr-node-accent,var(--fxr-accent));}</style>