<script setup>
import { computed } from 'vue'
import { CheckCircle2, RefreshCw } from 'lucide-vue-next'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { projects } from '../../stores/projects'
import { session } from '../../stores/session'
import { useTaskFilters } from '../../composables/useTaskFilters'
import { due, calendar, statuses } from '../../utils/format'
import TaskFilters from '../../components/tasks/TaskFilters.vue'
import ProjectState from '../../components/project/ProjectState.vue'
const source=computed(()=>projects.state.tasks.filter(t=>t.assigned_to===session.state.user.id)), {filters,tasks,reset}=useTaskFilters(source), toast=useToast()
const label=status=>statuses.find(s=>s.value===status)?.label
async function refresh() { try { await projects.refresh() } catch(e) { toast.add({severity:'error',summary:e.friendly,life:4000}) } }
</script>
<template><ProjectState><div class="page-heading"><div><span class="eyebrow">YOUR FOCUS</span><h1>My tasks</h1><p>{{ source.filter(t=>t.status!=='DONE').length }} active tasks assigned to you in {{ projects.active.value?.name }}.</p></div><Button label="Refresh" severity="secondary" :loading="projects.state.loading" @click="refresh"><template #icon><RefreshCw :size="16" /></template></Button></div><TaskFilters :modelValue="filters" @clear="reset" /><section class="panel my-task-list"><button v-for="task in tasks" :key="task.id" class="my-task-row" @click="projects.openTask(task.id)"><span class="task-reference">TF-{{ task.id }}</span><div class="my-task-title"><strong>{{ task.title }}</strong><span :class="{ overdue: due(task)==='Overdue' }">{{ due(task) }} · {{ calendar(task.deadline) }}</span></div><span :class="['priority',task.priority.toLowerCase()]"><i></i>{{ task.priority }}</span><span class="role-badge">{{ label(task.status) }}</span><div class="list-progress"><div class="progress-track"><span :style="{width:`${task.progress}%`}"></span></div><span>{{ task.progress }}%</span></div></button><div v-if="!tasks.length" class="empty-state"><CheckCircle2 :size="30" /><h3>{{ source.length ? 'No tasks match your filters.' : 'Your focus is clear.' }}</h3><p>{{ source.length ? 'Try clearing or changing your filters.' : 'Tasks assigned to you will appear here. You can explore the team’s work on the board.' }}</p><Button v-if="source.length" label="Clear filters" severity="secondary" @click="reset" /><RouterLink v-else to="/board">Open task board</RouterLink></div></section></ProjectState></template>
