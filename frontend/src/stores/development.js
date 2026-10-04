import { reactive } from 'vue'
import { api } from '../services/api'
import { projects } from './projects'
import { workspace } from './workspace'

const state=reactive({config:null,canManage:false,canExecute:false,enabled:false,suggestions:{},latestTest:null,fingerprint:'',execution:null,terminal:false,settings:false,importDialog:false,busy:false,error:''})
let generation=0
function clear(){generation++;Object.assign(state,{config:null,canManage:false,canExecute:false,execution:null,latestTest:null,terminal:false,settings:false,importDialog:false,error:''})}
async function load(){
  const pid=projects.state.activeId,ticket=generation;if(!pid)return
  const {data}=await api.get(`/projects/${pid}/development`)
  if(ticket!==generation || pid!==projects.state.activeId)return
  Object.assign(state,{config:data.config,canManage:data.can_manage,canExecute:data.can_execute,enabled:data.enabled,suggestions:data.suggestions,latestTest:data.latest_test,fingerprint:data.fingerprint})
  if(!data.can_execute){state.execution=null;return}
  if(!state.execution){const r=await api.get(`/projects/${pid}/executions`);if(ticket===generation)state.execution=r.data.executions[0] || null}
}
function update(value){if(value.project_id!==projects.state.activeId)return;state.execution=value;if(value.kind==='test')state.latestTest=value}
async function start(kind,command){
  if(state.busy)return
  state.error='';state.busy=true
  try{
    if(workspace.dirty.value && !await workspace.save())throw new Error('Save failed. Resolve the file before executing.')
    const {data}=await api.post(`/projects/${projects.state.activeId}/executions`,{kind,command})
    update(data.execution);state.terminal=true
  }catch(e){state.error=e.friendly || e.message;state.terminal=true}finally{state.busy=false}
}
async function stop(){try{await api.post(`/projects/${projects.state.activeId}/executions/${state.execution.id}/stop`)}catch(e){state.error=e.friendly}}
async function poll(){if(!state.execution)return;try{const {data}=await api.get(`/projects/${projects.state.activeId}/executions/${state.execution.id}`);update(data.execution)}catch(e){state.error=e.friendly}}
async function download(){
  state.error='';state.busy=true
  try{if(workspace.dirty.value && !await workspace.save())throw new Error('Save failed; the ZIP was not exported.')
    const response=await api.post(`/projects/${projects.state.activeId}/workspace/export`,{},{responseType:'blob'})
    const url=URL.createObjectURL(response.data),a=document.createElement('a');a.href=url;a.download=`${projects.active.value.name.replace(/[^a-zA-Z0-9_-]/g,'_')}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
  }catch(e){state.error=e.friendly || e.message}finally{state.busy=false}
}
export const development={state,load,clear,start,stop,poll,update,download}
