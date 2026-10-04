<script setup>
import { ref, computed, watch } from 'vue'
import draggable from 'vuedraggable'
import Button from 'primevue/button'
import { Plus, RefreshCw } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { projects } from '../../stores/projects'
import { session } from '../../stores/session'
import { statuses } from '../../utils/format'
import { useTaskFilters } from '../../composables/useTaskFilters'
import TaskFilters from '../../components/tasks/TaskFilters.vue'
import TaskCard from '../../components/tasks/TaskCard.vue'
import ProjectState from '../../components/project/ProjectState.vue'
const source = computed(()=>projects.state.tasks), { filters,tasks,reset }=useTaskFilters(source), columns=ref({}), toast=useToast(), dragging=ref(false)
const leader=computed(()=>session.state.team?.role==='LEADER')
const canEdit=t=>leader.value || t.assigned_to===session.state.user.id
function rebuild() { columns.value=Object.fromEntries(statuses.map(s=>[s.value,tasks.value.filter(t=>t.status===s.value)])) }
watch(tasks,rebuild,{immediate:true})
async function changed(event,status) {
  if(!event.added) return
  const item=projects.state.tasks.find(t=>t.id===event.added.element.id)
  if(!item || item.status===status) return
  try { await projects.patchTask(item,{status},true); toast.add({severity:'success',summary:'Task moved',life:2500}) }
  catch(e) { rebuild(); toast.add({severity:'error',summary:e.friendly,life:4500}) }
}
async function refresh() { try { await projects.refresh() } catch(e) { toast.add({severity:'error',summary:e.friendly,life:4500}) } }
const animation=window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 160
</script>
<template><ProjectState><div class="page-heading"><div><span class="eyebrow">WORK IN MOTION</span><h1>Task board</h1><p>{{ tasks.length }} of {{ projects.state.tasks.length }} tasks · Drag the grip to move work, or open a task to change its status.</p></div><div class="d-flex gap-2"><Button aria-label="Refresh project" severity="secondary" :loading="projects.state.loading" @click="refresh"><RefreshCw :size="16" /></Button><Button v-if="leader" label="Create task" @click="projects.state.createTask=true"><template #icon><Plus :size="16" /></template></Button></div></div><TaskFilters :modelValue="filters" assignee @clear="reset" /><div v-if="!projects.state.tasks.length" class="board-intro"><p>{{ leader ? 'A blank board is a fresh start. Create your first task to bring this project to life.' : 'No tasks have been created for this project yet.' }}</p></div><div :class="['kanban',{dragging}]" aria-label="Task status board"><section v-for="status in statuses" :key="status.value" :class="['kanban-column',status.value.toLowerCase()]"><header><span class="status-dot"></span><h2>{{ status.label }}</h2><span class="count-badge">{{ columns[status.value]?.length || 0 }}</span></header><draggable v-model="columns[status.value]" :group="`tasks-${projects.state.activeId}`" item-key="id" handle=".drag-handle" :animation="animation" :disabled="projects.state.busy" :move="event=>canEdit(event.draggedContext.element)" ghost-class="drag-ghost" chosen-class="drag-chosen" drag-class="drag-floating" class="column-tasks" @change="changed($event,status.value)" @start="dragging=true" @end="dragging=false"><template #item="{element}"><TaskCard :task="element" :draggable="canEdit(element)" /></template></draggable><p v-if="!columns[status.value]?.length" class="column-empty">{{ tasks.length ? 'No tasks in this status' : 'Nothing here yet' }}</p></section></div></ProjectState></template>
