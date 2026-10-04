import { reactive, computed } from 'vue'
import { api } from '../services/api'
import { projects } from './projects'
import { session } from './session'

const state=reactive({nodes:[],rootPermission:'VIEW',active:null,detail:null,text:'',base:'',version:null,loading:false,saving:false,error:'',conflict:null,revision:0,explorer:true,context:true,inWorkspace:false})
const dirty=computed(()=>state.active?.kind==='file' && state.text!==state.base)
let generation=0
function key(id=state.active?.id) { return `teamflow.draft.${session.state.user?.id}.${state.active?.project_id || projects.state.activeId}.${id}` }
function draft() {
  if(!state.active || state.active.kind!=='file')return
  try { if(dirty.value) sessionStorage.setItem(key(),JSON.stringify({text:state.text,base:state.base,version:state.version})); else sessionStorage.removeItem(key()) } catch {state.error='Browser draft storage is full. Save or download your draft before leaving.'}
}
function edit(text) {state.text=text; draft()}
function clear() {draft(); generation++; state.nodes=[];state.active=null;state.detail=null;state.text='';state.base='';state.version=null;state.error='';state.conflict=null;state.loading=false}
async function tree() {
  const id=projects.state.activeId, ticket=generation
  if(!id)return
  const {data}=await api.get(`/projects/${id}/workspace`)
  if(ticket!==generation || id!==projects.state.activeId)return
  state.nodes=data.nodes;state.rootPermission=data.root_permission
}
async function open(id) {
  const projectId=projects.state.activeId,ticket=++generation
  draft();state.loading=true;state.error='';state.conflict=null
  try {
    const {data}=await api.get(`/workspace/nodes/${id}`)
    if(ticket!==generation || projectId!==projects.state.activeId)return
    if(data.node.project_id!==projectId)throw new Error('This file belongs to another project.')
    state.active=data.node;state.detail=data;state.base=data.node.content || '';state.text=state.base;state.version=data.node.version
    const saved=sessionStorage.getItem(key(id))
    if(saved && data.node.kind==='file') {try {const restored=JSON.parse(saved);state.text=restored.text;state.base=restored.base;state.version=restored.version;if(restored.version!==data.node.version)state.conflict=data.node} catch {sessionStorage.removeItem(key(id))}}
  } catch(e) {if(ticket===generation)state.error=e.friendly || e.message}
  finally {if(ticket===generation)state.loading=false}
}
async function refresh() {
  const id=state.active?.id,ticket=generation,wasDirty=dirty.value
  await tree()
  if(!id || ticket!==generation)return
  const current=state.nodes.find(n=>n.id===id)
  if(!current) {draft();state.active=null;state.detail=null;state.error='This node was deleted or your access changed. Your unsaved draft remains in this browser session.';return}
  const {data}=await api.get(`/workspace/nodes/${id}`)
  if(ticket!==generation || state.active?.id!==id)return
  state.detail=data;state.active=data.node
  if(wasDirty || dirty.value) {if(data.node.version!==state.version)state.conflict=data.node}
  else {state.text=data.node.content || '';state.base=state.text;state.version=data.node.version;state.conflict=null}
  state.revision++
}
async function save() {
  if(!state.active || state.saving || !dirty.value)return false
  if(!['EDIT','FULL_ACCESS'].includes(state.active.permission)){state.error='This file is read only. Your draft is preserved.';return false}
  const id=state.active.id,text=state.text,version=state.version
  state.saving=true;state.error=''
  try {
    const {data}=await api.patch(`/workspace/nodes/${id}`,{content:text,version})
    if(state.active?.id===id){state.active=data.node;state.base=text;state.version=data.node.version;state.conflict=null;draft();await refresh()}
    return true
  } catch(e) {state.error=e.friendly;if(e.response?.status===409)state.conflict=e.response.data.current || {};draft();return false}
  finally {state.saving=false}
}
function downloadDraft(){const url=URL.createObjectURL(new Blob([state.text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=state.active?.name || 'teamflow-draft.txt';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
async function downloadAsset(){try{const response=await api.get(`/workspace/nodes/${state.active.id}/download`,{responseType:'blob'});const url=URL.createObjectURL(response.data),a=document.createElement('a');a.href=url;a.download=state.active.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){state.error=e.friendly}}
export const workspace={state,dirty,clear,tree,open,refresh,save,edit,draft,downloadDraft,downloadAsset}
