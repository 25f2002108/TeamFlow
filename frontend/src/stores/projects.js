import { reactive, computed } from 'vue'
import { api } from '../services/api'
import { session } from './session'
import { today } from '../utils/format'

const state = reactive({ projects: [], activeId: null, tasks: [], dashboard: null, activity: [], hasMore: false, loading: false, error: '', taskId: null, createTask: false, projectDialog: false, editingProject: false, palette: false, busy: false })
const active = computed(() => state.projects.find(p => p.id === state.activeId))
let generation = 0
function clear() { generation++; state.projects = []; state.activeId = null; state.tasks = []; state.dashboard = null; state.activity = []; state.taskId = null; state.error = ''; state.loading = false; state.createTask = false; state.projectDialog = false }
function storageKey() { return `teamflow.project.${session.state.user?.id}.${session.state.activeId}` }
async function loadProjects() {
  const teamId = session.state.activeId, userId = session.state.user?.id
  clear()
  if (!teamId) return
  const ticket = generation
  state.loading = true
  try {
    const { data } = await api.get(`/teams/${teamId}/projects`)
    if (ticket !== generation || teamId !== session.state.activeId || userId !== session.state.user?.id) return
    state.projects = data.projects
    const saved = Number(localStorage.getItem(storageKey()))
    await select(state.projects.some(p => p.id === saved) ? saved : state.projects[0]?.id)
  } catch (e) { if (ticket === generation) state.error = e.friendly }
  finally { if (!state.activeId && ticket === generation) state.loading = false }
}
async function select(id) {
  generation++
  state.activeId = id || null; state.tasks = []; state.dashboard = null; state.activity = []; state.taskId = null; state.error = ''; state.createTask = false
  localStorage.setItem(storageKey(), String(state.activeId || ''))
  if (id) await refresh(); else state.loading = false
}
async function refresh() {
  const id = state.activeId, ticket = generation
  if (!id) return
  state.loading = true; state.error = ''
  try {
    const results = await Promise.all([api.get(`/projects/${id}/tasks`), api.get(`/projects/${id}/dashboard`, { params: { today: today() } }), api.get(`/projects/${id}/activity`), api.get(`/projects/${id}`)])
    if (ticket !== generation) return
    state.tasks = results[0].data.tasks; state.dashboard = results[1].data.dashboard; state.activity = results[2].data.activity; state.hasMore = results[2].data.has_more
    const index = state.projects.findIndex(p => p.id === id)
    if (index !== -1) state.projects[index] = results[3].data.project
  } catch (e) { if (ticket === generation) state.error = e.friendly; throw e }
  finally { if (ticket === generation) state.loading = false }
}
async function patchTask(task, changes, optimistic=false) {
  if (state.busy) return false
  state.busy = true
  const id = state.activeId, snapshot = [...state.tasks]
  if (optimistic) state.tasks = state.tasks.map(t => t.id === task.id ? { ...t, ...changes, progress: changes.status === 'DONE' ? 100 : t.status === 'DONE' ? 0 : t.progress } : t)
  try {
    await api.patch(`/tasks/${task.id}`, { ...changes, version: task.version })
    if (id === state.activeId) await refresh()
    return true
  } catch (e) { if (id === state.activeId) state.tasks = snapshot; throw e }
  finally { state.busy = false }
}
function newProject() { state.editingProject = false; state.projectDialog = true }
function editProject() { state.editingProject = true; state.projectDialog = true }
function openTask(id) { state.taskId = id }
export const projects = { state, active, clear, loadProjects, select, refresh, patchTask, newProject, editProject, openTask }
