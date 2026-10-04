import { reactive, computed } from 'vue'
import { api } from '../services/api'

const state = reactive({ user: null, teams: [], activeId: null, ready: false, error: '', team: null, members: [], loading: false })
let initialization
let requestVersion = 0
const activeTeam = computed(() => state.teams.find(t => t.id === state.activeId))
function apply(data) {
  state.user = data.user
  state.teams = data.teams
  let stored = Number(localStorage.getItem('teamflow.activeTeam'))
  selectTeam(state.teams.some(t => t.id === state.activeId) ? state.activeId : state.teams.some(t => t.id === stored) ? stored : state.teams[0]?.id)
}
function selectTeam(id) {
  state.activeId = id || null
  localStorage.setItem('teamflow.activeTeam', String(state.activeId || ''))
  state.team = null
  state.members = []
  requestVersion++
}
async function restore() {
  state.error = ''
  try { apply((await api.get('/auth/me')).data) }
  catch (error) { if (error.response?.status === 401) clear(); else state.error = error.friendly }
  finally { state.ready = true }
}
function init() { return initialization ||= restore() }
async function refresh() { apply((await api.get('/auth/me')).data) }
function clear() { state.user = null; state.teams = []; selectTeam(null) }
async function logout() { await api.post('/auth/logout'); clear() }
async function loadTeam() {
  const id = state.activeId
  if (!id) return
  const version = ++requestVersion
  state.loading = true
  try {
    const { data } = await api.get(`/teams/${id}`)
    if (version === requestVersion) {
      state.team = data.team; state.members = data.members
      const index = state.teams.findIndex(t => t.id === id)
      if (index !== -1) state.teams[index] = data.team
    }
  } catch (error) {
    if (error.response?.status === 403) await refresh()
    throw error
  } finally { if (version === requestVersion) state.loading = false }
}
export const session = { state, activeTeam, init, restore, refresh, apply, selectTeam, logout, clear, loadTeam }
