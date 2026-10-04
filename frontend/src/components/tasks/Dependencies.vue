<script setup>
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Select from 'primevue/select'
import { projects } from '../../stores/projects'
import { session } from '../../stores/session'
import { api } from '../../services/api'
const props=defineProps({task:Object}),emit=defineEmits(['changed']),chosen=ref(),busy=ref(false),error=ref('')
const leader=computed(()=>session.state.team.role==='LEADER')
const dependencies=computed(()=>projects.state.tasks.filter(t=>props.task.depends_on?.includes(t.id)))
const blocks=computed(()=>projects.state.tasks.filter(t=>props.task.blocks?.includes(t.id)))
const options=computed(()=>projects.state.tasks.filter(t=>t.id!==props.task.id && !props.task.depends_on?.includes(t.id)))
async function update(id,remove=false){busy.value=true;error.value='';try{if(remove)await api.delete(`/tasks/${props.task.id}/dependencies/${id}`);else await api.post(`/tasks/${props.task.id}/dependencies`,{depends_on_id:id});chosen.value=null;await projects.refresh();emit('changed')}catch(e){error.value=e.friendly}finally{busy.value=false}}
</script>
<template><section class="dependency-section"><h3>Dependencies</h3><p v-if="task.blocked" class="blocked-label">Blocked — complete the unfinished prerequisites below.</p><strong>Depends on</strong><div v-for="t in dependencies" :key="t.id" class="dependency-row"><button class="text-button" @click="projects.openTask(t.id)">TF-{{ t.id }} · {{ t.title }} · {{ t.status.replaceAll('_',' ') }}</button><Button v-if="leader" :aria-label="`Remove dependency ${t.title}`" label="Remove" text :disabled="busy" @click="update(t.id,true)"/></div><p v-if="!dependencies.length" class="field-hint">No prerequisites.</p><div v-if="leader" class="dependency-add"><Select v-model="chosen" :options="options" optionLabel="title" optionValue="id" placeholder="Choose prerequisite" aria-label="Dependency task" filter/><Button label="Add dependency" :disabled="!chosen" :loading="busy" @click="update(chosen)"/></div><strong>Blocks</strong><button v-for="t in blocks" :key="t.id" class="dependency-link" @click="projects.openTask(t.id)">TF-{{ t.id }} · {{ t.title }}</button><p v-if="!blocks.length" class="field-hint">No dependent tasks.</p><p v-if="error" role="alert" class="form-error">{{ error }}</p></section></template>
