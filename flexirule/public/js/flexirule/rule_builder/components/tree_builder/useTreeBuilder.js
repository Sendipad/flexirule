import {computed,nextTick,reactive,ref,watch} from "vue";
import {cloneTree,findNode,findPath,isContainerNode,normalizeTree,treesEqual} from "./tree_builder_utils.js";
import * as commands from "./tree_builder_commands.js";
import {validateTree} from "./tree_builder_validation.js";
export function useTreeBuilder({modelValue,emit,readOnly=false,groupOperators=["and","or"],leafFactory=()=>({}),scopeFactory=()=>({}),allowScopes=true,allowEmptyGroups=true,validateLeaf,validateScope}={}){
const root=reactive(normalizeTree(modelValue?.value ?? modelValue,{groupOperators})),selectedNodeId=ref(null),focusedNodeId=ref(null),editingNodeId=ref(null),expandedNodes=reactive(new Set([root.id])),dragState=reactive({nodeId:null});let syncing=false;
const operators=computed(()=>groupOperators.filter(Boolean)),selectedNode=computed(()=>findNode(root,selectedNodeId.value)),focusedNode=computed(()=>findNode(root,focusedNodeId.value));
function replaceRoot(next){const n=normalizeTree(next,{groupOperators});Object.keys(root).forEach(k=>delete root[k]);Object.assign(root,n);expandedNodes.clear();expandedNodes.add(root.id);}
function emitChange(){if(syncing||!emit)return;const n=cloneTree(root);emit("update:modelValue",n);emit("change",n);}
function mutate(fn){if(readOnly)return null;const result=fn(root);if(result!==false)emitChange();return result;}
const addLeaf=(p=root.id,payload)=>mutate(t=>commands.addLeaf(t,p,payload??leafFactory()));
const addGroup=(p=root.id,op=operators.value[0]||"and")=>mutate(t=>commands.addGroup(t,p,op));
const addScope=(p=root.id,scope)=>mutate(t=>commands.addScope(t,p,scope??scopeFactory()));
const removeNode=id=>{const r=mutate(t=>commands.removeNode(t,id));if(r){if(selectedNodeId.value===id)selectedNodeId.value=null;if(focusedNodeId.value===id)focusedNodeId.value=null;if(editingNodeId.value===id)editingNodeId.value=null;}return r;};
const moveNode=(id,p,pos=-1)=>mutate(t=>commands.moveNode(t,id,p,pos));
const setOperator=(id,op)=>operators.value.includes(op)&&mutate(t=>commands.setOperator(t,id,op));
const replaceNode=(id,n)=>mutate(t=>commands.replaceNode(t,id,n));
function reset(next=modelValue?.value ?? modelValue){syncing=true;replaceRoot(next);nextTick().then(()=>syncing=false);}
function toggleExpanded(id){expandedNodes.has(id)?expandedNodes.delete(id):expandedNodes.add(id);}
function getNodeContext(id){const path=findPath(root,id);return {scopes:path.filter(n=>n.type==="scope").map(n=>cloneTree(n.scope)),path:path.map(n=>({id:n.id,type:n.type}))};}
function canMove(id,target){if(!id||!target||id===root.id||id===target)return false;const path=findPath(root,target).map(n=>n.id);return !!findNode(root,id)&&isContainerNode(findNode(root,target))&&!path.includes(id);}
function validate(){return validateTree(root,{groupOperators:operators.value,allowScopes,allowEmptyGroups,validateLeaf,validateScope});}
function beginDrag(id){if(!readOnly)dragState.nodeId=id;}function dropNode(target,pos=-1){if(!dragState.nodeId)return false;const r=moveNode(dragState.nodeId,target,pos);dragState.nodeId=null;return r;}
watch(modelValue,async v=>{const n=normalizeTree(v,{groupOperators});if(treesEqual(n,root))return;syncing=true;replaceRoot(n);await nextTick();syncing=false;},{deep:true});
return {root,selectedNode,focusedNode,selectedNodeId,focusedNodeId,editingNodeId,expandedNodes,dragState,operators,addLeaf,addGroup,addScope,removeNode,moveNode,setOperator,replaceNode,reset,selectNode:id=>selectedNodeId.value=id,focusNode:id=>focusedNodeId.value=id,setEditing:id=>editingNodeId.value=id,toggleExpanded,isExpanded:id=>expandedNodes.has(id),getNodeContext,canMove,validate,beginDrag,dropNode,getTree:()=>cloneTree(root)};
}