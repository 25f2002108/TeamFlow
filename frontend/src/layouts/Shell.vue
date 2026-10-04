<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu as MenuIcon, Plus, Users, ChevronDown, Search, FolderKanban, Pencil } from 'lucide-vue-next'
import Drawer from 'primevue/drawer'
import Menu from 'primevue/menu'
import Select from 'primevue/select'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'
import { useToast } from 'primevue/usetoast'
import SideNav from '../components/navigation/SideNav.vue'
import TeamForm from '../components/team/TeamForm.vue'
import ProjectDialog from '../components/project/ProjectDialog.vue'
import CreateTask from '../components/tasks/CreateTask.vue'
import TaskDrawer from '../components/tasks/TaskDrawer.vue'
import CommandPalette from '../components/navigation/CommandPalette.vue'
import CollaborationControls from '../components/navigation/CollaborationControls.vue'
import { collaboration } from '../stores/collaboration'
import { development } from '../stores/development'
import { workspace } from '../stores/workspace'
import { session } from '../stores/session'
import { projects } from '../stores/projects'
import { initials } from '../utils/format'
const route=useRoute(), router=useRouter(), toast=useToast()
const mobile=ref(false), teamDialog=ref(false), mode=ref('create'), profileMenu=ref(), loadError=ref(''), signingOut=ref(false)
const leader=computed(()=>session.state.team?.role==='LEADER')
async function signout() { if(signingOut.value)return; if(workspace.dirty.value && !window.confirm('Sign out? Save or download your draft first. Your browser draft is preserved.'))return;workspace.draft(); signingOut.value=true; try { collaboration.stop(); await session.logout(); projects.clear(); workspace.clear(); router.push('/login') } catch(e) { toast.add({severity:'error',summary:e.friendly,life:4000}) } finally { signingOut.value=false } }
const profileItems=[{label:'Account settings',command:()=>router.push('/settings')},{label:'Create or join a team',command:()=>teamDialog.value=true},{separator:true},{label:'Sign out',command:signout}]
let loadTicket=0
async function load() {
  const ticket=++loadTicket
  loadError.value=''; projects.clear()
  if(!session.state.activeId && session.state.user){router.replace('/onboarding');return}
  try { await session.loadTeam(); if(ticket===loadTicket) await projects.loadProjects() } catch(e) { if(ticket===loadTicket)loadError.value=e.friendly }
}
watch(()=>session.state.activeId,load,{immediate:true})
watch(()=>projects.state.activeId,async()=>{workspace.clear();development.clear();try{await workspace.tree();await development.load();await collaboration.context()}catch(e){collaboration.state.error=e.friendly}})
function shortcut(event) { if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault(); projects.state.palette=!projects.state.palette} }
onMounted(()=>{window.addEventListener('keydown',shortcut);collaboration.start()})
onUnmounted(()=>{window.removeEventListener('keydown',shortcut);loadTicket++;collaboration.stop();workspace.clear();projects.clear()})
function guardSwitch(){return !workspace.dirty.value || window.confirm('Switch context? Your unsaved draft will remain in this browser session.')}
async function selectTeam(id){if(guardSwitch()){workspace.draft();if(route.name==='Workspace')await router.replace('/workspace');session.selectTeam(id)}}
async function selectProject(id) { if(!guardSwitch())return;try {workspace.draft();if(route.name==='Workspace')await router.replace('/workspace'); await projects.select(id) } catch(e) { toast.add({severity:'error',summary:e.friendly,life:4000}) } }
</script>
<template><div :class="['app-shell',{'workspace-mode':route.name==='Workspace'}]"><a href="#main-content" class="skip-link">Skip to content</a><aside class="desktop-sidebar"><SideNav /></aside><Drawer v-model:visible="mobile" class="mobile-nav" header="Navigation"><SideNav @navigate="mobile=false" /></Drawer><div class="app-body"><header class="topbar"><div class="d-flex align-items-center gap-3 min-w-0"><button class="icon-button mobile-menu" aria-label="Open navigation" @click="mobile=true"><MenuIcon :size="20" /></button><span class="breadcrumb-team">{{ session.activeTeam.value?.name }}</span><span class="breadcrumb-divider">/</span><span>{{ route.name }}</span></div><div class="d-flex align-items-center gap-3"><button class="search-trigger" aria-label="Open command palette" @click="projects.state.palette=true"><Search :size="15" /><span>Search or jump to…</span><kbd>⌘ / Ctrl K</kbd></button><CollaborationControls /><button class="profile-trigger" aria-label="Open account menu" aria-haspopup="true" aria-controls="profile-menu" @click="profileMenu.toggle($event)"><span class="avatar avatar-small">{{ initials(session.state.user?.name) }}</span><ChevronDown :size="13" /></button><Menu ref="profileMenu" id="profile-menu" :model="profileItems" popup /></div></header><div class="context-strip"><div class="context-selector"><Users :size="16" /><Select :modelValue="session.state.activeId" :options="session.state.teams" optionLabel="name" optionValue="id" aria-label="Active team" class="team-select" @update:modelValue="selectTeam" /><button class="icon-button" aria-label="Create or join team" @click="teamDialog=true"><Plus :size="15" /></button></div><span class="context-divider"></span><div class="context-selector project-selector"><FolderKanban :size="16" /><Select v-if="projects.state.projects.length" :modelValue="projects.state.activeId" :options="projects.state.projects" optionLabel="name" optionValue="id" aria-label="Active project" class="team-select" @update:modelValue="selectProject" /><span v-else class="context-empty">{{ projects.state.loading?'Loading projects…':'No project yet' }}</span><button v-if="leader" class="icon-button" aria-label="Create project" @click="projects.newProject"><Plus :size="15" /></button><button v-if="leader && projects.state.activeId" class="icon-button" aria-label="Edit active project" @click="projects.editProject"><Pencil :size="14" /></button></div><span class="context-role">{{ leader?'Leader':'Member' }}</span></div><main id="main-content" class="main-content" tabindex="-1"><div v-if="loadError" class="panel error-panel" role="alert"><h2>We couldn’t load this team.</h2><p>{{ loadError }}</p><Button label="Retry" @click="load" /></div><div v-else-if="!session.state.team" class="loading-content" aria-label="Loading team"><Skeleton width="220px" height="32px" /><Skeleton class="mt-3" width="60%" height="18px" /><Skeleton class="mt-5" height="220px" /></div><RouterView v-else :key="`${session.state.activeId}-${projects.state.activeId}`" /></main><footer class="app-footer"><span>Built together. Moved forward.</span><span>TeamFlow / Project management</span></footer></div><Dialog v-model:visible="teamDialog" modal :header="mode==='create'?'Create a team':'Join a team'" :style="{width:'440px'}" :breakpoints="{'600px':'92vw'}"><div class="segmented mb-4"><button :class="{selected:mode==='create'}" @click="mode='create'">Create team</button><button :class="{selected:mode==='join'}" @click="mode='join'">Join team</button></div><TeamForm :key="mode" :mode="mode" @done="teamDialog=false" /></Dialog><ProjectDialog /><CreateTask /><TaskDrawer /><CommandPalette /></div></template>


