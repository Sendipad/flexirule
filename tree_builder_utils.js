import { TREE_NODE_TYPES, DEFAULT_GROUP_OPERATORS } from "./tree_builder_types.js";
export function createNodeId(prefix="tree"){if(typeof crypto!=="undefined"&&crypto.randomUUID)return crypto.randomUUID();return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,10)}`;}
export const createId=createNodeId;
export function cloneTree(v){return v==null?v:JSON.parse(JSON.stringify(v));}
export const isGroupNode=n=>!!n&&n.type===TREE_NODE_TYPES.GROUP;
export const isScopeNode=n=>!!n&&n.type===TREE_NODE_TYPES.SCOPE;
export const isLeafNode=n=>!!n&&n.type===TREE_NODE_TYPES.LEAF;
export const isContainerNode=n=>isGroupNode(n)||isScopeNode(n);
export const createGroup=(operator=DEFAULT_GROUP_OPERATORS[0],children=[])=>({id:createNodeId("group"),type:"group",operator,children:Array.isArray(children)?children:[]});
export const createScope=(scope={},children=[])=>({id:createNodeId("scope"),type:"scope",scope:cloneTree(scope)||{},children:Array.isArray(children)?children:[]});
export const createLeaf=(payload={})=>({id:createNodeId("leaf"),type:"leaf",...cloneTree(payload)});
export function walkTree(tree,visitor){if(!tree||typeof tree!=="object")return;visitor(tree);if(isContainerNode(tree))(tree.children||[]).forEach(c=>walkTree(c,visitor));}
export function findNode(tree,id){let r=null;walkTree(tree,n=>{if(!r&&n.id===id)r=n;});return r;}
export function findParent(tree,id){let r=null;function visit(n){if(!isContainerNode(n)||r)return;for(const c of n.children||[]){if(c.id===id){r=n;return;}visit(c);if(r)return;}}visit(tree);return r;}
export function findPath(tree,id){const p=[];function visit(n){if(!n)return false;p.push(n);if(n.id===id)return true;if(isContainerNode(n)){for(const c of n.children||[])if(visit(c))return true;}p.pop();return false;}return visit(tree)?p:[];}
export function isDescendant(node,id){if(!node||!id)return false;if(node.id===id)return true;return isContainerNode(node)&&(node.children||[]).some(c=>isDescendant(c,id));}
export function mapTree(tree,mapper){if(!tree||typeof tree!=="object")return tree;const n=mapper(tree);if(isContainerNode(n))n.children=(n.children||[]).map(c=>mapTree(c,mapper));return n;}
export function normalizeTree(value,{groupOperators=DEFAULT_GROUP_OPERATORS}={}){const ops=groupOperators.filter(Boolean);function norm(n){if(!n||typeof n!=="object")return null;const id=n.id||createNodeId(n.type||"tree");if(isGroupNode(n))return {...cloneTree(n),id,type:"group",operator:ops.includes(n.operator)?n.operator:ops[0],children:Array.isArray(n.children)?n.children.map(norm).filter(Boolean):[]};if(isScopeNode(n))return {...cloneTree(n),id,type:"scope",scope:cloneTree(n.scope)||{},children:Array.isArray(n.children)?n.children.map(norm).filter(Boolean):[]};if(isLeafNode(n)){const {children,operator,scope,...payload}=cloneTree(n);return {...payload,id,type:"leaf"};}return {...cloneTree(n),id,type:"leaf"};}const n=norm(value);return n&&isGroupNode(n)?n:createGroup(ops[0],n?[n]:[]);}
export const treesEqual=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
