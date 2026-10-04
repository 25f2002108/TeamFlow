<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import Select from 'primevue/select'
import Button from 'primevue/button'
import { FileCode2, ArrowUpRight, Unlink } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { api } from '../../services/api'
import { projects } from '../../stores/projects'
import { session } from '../../stores/session'
const props=defineProps({task:Object}),emit=defineEmits(['changed']),files=ref([]),available=ref([]),selected=ref(),busy=ref(false),error=ref(''),router=useRouter()
const leader=computed(()=>session.state.team?.role==='LEADER')
async function load(){try{files.value=(await api.get(`/tasks/${props.task.id}/files`)).data.files;if(leader.value){available.value=(await api.get(`/projects/${props.task.project_id}/workspace`)).data.nodes.filter(n=>n.kind==='file'&&!files.value.some(f=>f.id===n.id))}}catch(e){error.value=e.friendly}}
watch(()=>props.task.id,load,{immediate:true})
onMounted(()=>window.addEventListener('teamflow-project-updated',load));onBeforeUnmount(()=>window.removeEventListener('teamflow-project-updated',load))
async function link(){if(!selected.value)return;busy.value=true;error.value='';try{await api.post(`/tasks/${props.task.id}/files`,{node_id:selected.value});selected.value=null;await load();emit('changed')}catch(e){error.value=e.friendly}finally{busy.value=false}}
async function unlink(file){busy.value=true;try{await api.delete(`/tasks/${props.task.id}/files/${file.id}`);await load();emit('changed')}catch(e){error.value=e.friendly}finally{busy.value=false}}
function open(file){projects.state.taskId=null;router.push({path:'/workspace',query:{file:file.id,task:props.task.id}})}
</script>
<template><section class="related-files"><h3>Related project files</h3><p class="field-hint">Actual workspace files linked to this task. Your file permissions still apply.</p><p v-if="error" class="form-error" role="alert">{{ error }}</p><div v-if="leader" class="link-file-form"><Select v-model="selected" :options="available" optionLabel="path" optionValue="id" placeholder="Choose a workspace file" aria-label="Workspace file to link" :disabled="busy"/><Button label="Link file" :disabled="!selected" :loading="busy" @click="link"/></div><div v-for="file in files" :key="file.id" class="related-file-row"><FileCode2 :size="16"/><div><strong>{{ file.path }}</strong><span>{{ file.permission.replaceAll('_',' ').toLowerCase() }}</span></div><Button label="Open in Workspace" text size="small" @click="open(file)"><template #icon><ArrowUpRight :size="14"/></template></Button><Button v-if="leader" :aria-label="`Unlink ${file.path}`" text severity="secondary" :disabled="busy" @click="unlink(file)"><Unlink :size="14"/></Button></div><p v-if="!files.length" class="compact-empty">No accessible project files linked yet.</p></section></template>
