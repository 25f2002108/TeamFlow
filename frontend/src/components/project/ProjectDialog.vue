<script setup>
import { reactive, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { projects } from '../../stores/projects'
import { session } from '../../stores/session'
import { api } from '../../services/api'
const form = reactive({ name: '', description: '', deadline: '' }), busy = ref(false), error = ref(''), toast = useToast()
watch(() => projects.state.projectDialog, visible => { if (visible) { Object.assign(form, projects.state.editingProject ? { name: projects.active.value.name, description: projects.active.value.description, deadline: projects.active.value.deadline || '' } : { name: '', description: '', deadline: '' }); error.value = '' } })
async function save() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    const editing = projects.state.editingProject, teamId = session.state.activeId
    const { data } = await api[editing ? 'patch' : 'post'](editing ? `/projects/${projects.state.activeId}` : `/teams/${teamId}/projects`, { ...form, deadline: form.deadline || null })
    if (teamId !== session.state.activeId) return
    if (editing) { await projects.refresh() } else { projects.state.projects.push(data.project); await projects.select(data.project.id) }
    projects.state.projectDialog = false
    toast.add({ severity: 'success', summary: editing ? 'Project updated' : 'Project created', life: 3000 })
  } catch (e) { error.value = e.friendly } finally { busy.value = false }
}
</script>
<template><Dialog v-model:visible="projects.state.projectDialog" modal :header="projects.state.editingProject ? 'Edit project' : 'Create a project'" :style="{ width: '520px' }" :breakpoints="{ '600px': '92vw' }" :closable="!busy" :closeOnEscape="!busy"><form class="form-stack" @submit.prevent="save"><label for="project-name">Project name</label><InputText id="project-name" v-model="form.name" minlength="2" maxlength="120" required :disabled="busy" autofocus /><label for="project-description">Description</label><Textarea id="project-description" v-model="form.description" rows="4" maxlength="10000" :disabled="busy" placeholder="What are you building?" /><label for="project-deadline">Deadline (optional)</label><InputText id="project-deadline" v-model="form.deadline" type="date" :disabled="busy" /><p v-if="error" class="form-error" role="alert">{{ error }}</p><Button type="submit" :label="projects.state.editingProject ? 'Save project' : 'Create project'" :loading="busy" /></form></Dialog></template>
