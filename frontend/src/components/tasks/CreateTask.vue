<script setup>
import { reactive, watch, ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { projects } from '../../stores/projects'
import { api } from '../../services/api'
import TaskFields from './TaskFields.vue'
const form = reactive({}), busy = ref(false), error = ref(''), toast = useToast()
watch(() => projects.state.createTask, visible => { if (visible) { Object.assign(form, { title: '', description: '', assigned_to: null, estimated_duration:1, priority: 'MEDIUM', deadline: '', status: 'TODO', progress: 0 }); error.value = '' } })
async function save() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { const id = projects.state.activeId; await api.post(`/projects/${id}/tasks`, { ...form, deadline: form.deadline || null }); if (id === projects.state.activeId) { await projects.refresh(); projects.state.createTask = false } toast.add({ severity: 'success', summary: 'Task created', life: 3000 }) }
  catch (e) { error.value = e.friendly } finally { busy.value = false }
}
</script>
<template><Dialog v-model:visible="projects.state.createTask" modal header="Create a task" :style="{ width: '620px' }" :breakpoints="{ '680px': '94vw' }" :closable="!busy" :closeOnEscape="!busy"><form @submit.prevent="save"><TaskFields :modelValue="form" leader editable :busy="busy" /><p v-if="error" role="alert" class="form-error">{{ error }}</p><div class="form-actions d-flex justify-content-end"><Button type="submit" label="Create task" :loading="busy" /></div></form></Dialog></template>
