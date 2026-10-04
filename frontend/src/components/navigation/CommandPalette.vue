<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import { useToast } from 'primevue/usetoast'
import { Search, ArrowUpRight, Command } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { projects } from '../../stores/projects'
import { session } from '../../stores/session'
import { api } from '../../services/api'
import { development } from '../../stores/development'
import { workspace } from '../../stores/workspace'
const remoteResults=ref([]);let searchTimer,searchTicket=0
const query=ref(''), selected=ref(0), router=useRouter()
const toast=useToast()
const results=computed(()=>{
  const navigation=[['Overview','/'],['My tasks','/my-tasks'],['Task board','/board'],['Workspace','/workspace'],['Team','/team'],['Activity','/activity'],['Settings','/settings']].map(([label,path])=>({type:'GO TO',label,action:()=>router.push(path)}))
  if(session.state.team?.role==='LEADER') { navigation.push({type:'ACTION',label:'Create project',action:projects.newProject}); if(projects.state.activeId) navigation.push({type:'ACTION',label:'Create task',action:()=>projects.state.createTask=true}) }
  if(development.state.canManage){navigation.push({type:'ACTION',label:'Project settings',action:async()=>{await router.push('/workspace');development.state.settings=true}});navigation.push({type:'ACTION',label:'Download project',action:development.download})}
  if(workspace.state.rootPermission==='FULL_ACCESS' && projects.state.activeId)navigation.push({type:'ACTION',label:'Create file',action:async()=>{await router.push('/workspace');window.dispatchEvent(new CustomEvent('teamflow-create-file'))}})
  const switches=[...projects.state.projects.map(p=>({type:'SWITCH PROJECT',label:p.name,action:async()=>{await projects.select(p.id); router.push('/')}})),...session.state.teams.map(t=>({type:'SWITCH TEAM',label:t.name,action:()=>{session.selectTeam(t.id); router.push('/')}}))]
  const q=query.value.trim().toLowerCase()
  const content=q ? [...projects.state.tasks.map(t=>({type:'TASK',label:t.title,action:()=>projects.openTask(t.id)})),...workspace.state.nodes.filter(n=>n.kind==='file').map(n=>({type:'FILE',label:n.path,action:()=>router.push({path:'/workspace',query:{file:n.id}})})),...session.state.members.map(m=>({type:'MEMBER',label:`${m.name} · ${m.email}`,action:()=>router.push({path:'/team',query:{search:m.name}})}))] : []
  return [...navigation,...switches,...content,...remoteResults.value.map(r=>({...r,action:()=>r.node_id?router.push({path:'/workspace',query:{file:r.node_id,task:r.task_id}}):projects.openTask(r.task_id)}))].filter(item=>`${item.type} ${item.label}`.toLowerCase().includes(q)).slice(0,30)
})
watch(()=>projects.state.palette,visible=>{if(visible){query.value='';selected.value=0}})
watch(query,()=>{selected.value=0;remoteResults.value=[];clearTimeout(searchTimer);const ticket=++searchTicket;if(query.value.trim().length<2 || !projects.state.activeId)return;searchTimer=setTimeout(async()=>{try{const {data}=await api.get(`/projects/${projects.state.activeId}/search`,{params:{q:query.value}});if(ticket===searchTicket)remoteResults.value=data.results}catch{}},250)})
onBeforeUnmount(()=>clearTimeout(searchTimer))
async function run(item) { if(!item) return; if(workspace.dirty.value && !window.confirm('Open this result? Your unsaved draft will remain in this browser session.'))return;projects.state.palette=false; try { await item.action() } catch (e) { toast.add({severity:'error',summary:e.friendly || 'Unable to complete this command.',life:4500}) } }
function move(direction) { if(results.value.length) selected.value=(selected.value+direction+results.value.length)%results.value.length }
</script>
<template><Dialog v-model:visible="projects.state.palette" modal :showHeader="false" class="command-palette" :style="{width:'620px'}" :breakpoints="{'680px':'94vw'}"><div class="palette-input"><Search :size="19" /><InputText v-model="query" autofocus aria-label="Search commands, tasks, files and comments" placeholder="Search tasks, files, comments, people…" @keydown.down.prevent="move(1)" @keydown.up.prevent="move(-1)" @keydown.enter.prevent="run(results[selected])" /><kbd>esc</kbd></div><div class="palette-results" role="listbox" aria-label="Commands and search results"><button v-for="(item,index) in results" :key="`${item.type}-${item.label}`" :class="{selected:index===selected}" role="option" :aria-selected="index===selected" @click="run(item)" @mouseenter="selected=index"><span>{{ item.type }}</span><strong>{{ item.label }}</strong><ArrowUpRight :size="15" /></button><div v-if="!results.length" class="compact-empty">No matching tasks, teammates or commands.</div></div><footer><span><Command :size="13" /> Enter to open · ↑↓ to navigate</span><span>Search your current project</span></footer></Dialog></template>
