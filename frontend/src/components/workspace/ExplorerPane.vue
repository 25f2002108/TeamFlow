<script setup>
import { ref, reactive, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Menu from 'primevue/menu'
import ContextMenu from 'primevue/contextmenu'
import { FilePlus2, FolderPlus, RefreshCw, Search } from 'lucide-vue-next'
import FileTree from './FileTree.vue'
import { workspace } from '../../stores/workspace'
import { session } from '../../stores/session'
const emit=defineEmits(['open','create','rename','delete','permissions','refresh'])
const query=ref(''),expanded=reactive({}),menu=ref(),contextMenu=ref(),items=ref([])
const visible=computed(()=>{const nodes=workspace.state.nodes,q=query.value.trim().toLowerCase();if(!q)return nodes;const ids=new Set();for(const n of nodes.filter(n=>n.path.toLowerCase().includes(q))){let cursor=n;while(cursor){ids.add(cursor.id);cursor=nodes.find(p=>p.id===cursor.parent_id)}}return nodes.filter(n=>ids.has(n.id))})
const opened=computed(()=>query.value?Object.fromEntries(workspace.state.nodes.filter(n=>n.kind==='folder').map(n=>[n.id,true])):expanded)
function toggle(node){expanded[node.id]=!expanded[node.id]}
function actions({event,node}){
  items.value=[{label:node.kind==='file'?'Open file':'Expand / collapse',command:()=>node.kind==='file'?emit('open',node):toggle(node)}]
  if(node.permission==='FULL_ACCESS'){
    if(node.kind==='folder')items.value.push({label:'New file here',command:()=>emit('create',{kind:'file',parent:node})},{label:'New folder here',command:()=>emit('create',{kind:'folder',parent:node})})
    items.value.push({label:'Rename',command:()=>emit('rename',node)},{label:'Delete',command:()=>emit('delete',node)})
  }
  if(session.state.team?.role==='LEADER')items.value.push({label:'Permissions',command:()=>emit('permissions',node)})
  if(event.type==='contextmenu')contextMenu.value.show(event);else menu.value.toggle(event)
}
</script>
<template><section class="explorer-pane"><header><span class="eyebrow">PROJECT FILES</span><div><button v-if="workspace.state.rootPermission==='FULL_ACCESS'" class="icon-button" aria-label="New root file" title="New file" @click="$emit('create',{kind:'file',parent:null})"><FilePlus2 :size="16"/></button><button v-if="workspace.state.rootPermission==='FULL_ACCESS'" class="icon-button" aria-label="New root folder" title="New folder" @click="$emit('create',{kind:'folder',parent:null})"><FolderPlus :size="16"/></button><button class="icon-button" aria-label="Refresh workspace" title="Refresh" @click="$emit('refresh')"><RefreshCw :size="15"/></button></div></header><div class="explorer-search"><Search :size="14"/><InputText v-model="query" aria-label="Search workspace files" placeholder="Find a file or folder…"/></div><FileTree :nodes="visible" :expanded="opened" :activeId="workspace.state.active?.id" @toggle="toggle" @open="$emit('open',$event)" @menu="actions"/><div v-if="!visible.length" class="compact-empty">{{ query?'No matching files.':'Your workspace is ready. Create a folder or file to begin.' }}</div><footer><span>{{ workspace.state.nodes.filter(n=>n.kind==='file').length }} accessible files</span><span>Stored in this project</span></footer><Menu ref="menu" :model="items" popup/><ContextMenu ref="contextMenu" :model="items"/></section></template>
