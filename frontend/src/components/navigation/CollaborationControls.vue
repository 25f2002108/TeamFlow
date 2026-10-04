<script setup>
import { computed, ref } from 'vue'
import { Bell, Radio, CheckCheck, ArrowUpRight } from 'lucide-vue-next'
import Popover from 'primevue/popover'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import { useRouter } from 'vue-router'
import { collaboration } from '../../stores/collaboration'
import { session } from '../../stores/session'
import { projects } from '../../stores/projects'
import { workspace } from '../../stores/workspace'
import { initials, timestamp } from '../../utils/format'
const presence=ref(),router=useRouter(),error=ref(''),busy=ref(false)
const users=computed(()=>collaboration.state.users.filter(u=>u.project_id===projects.state.activeId))
async function mark(id){try{await collaboration.markRead(id)}catch(e){error.value=e.friendly}}
async function all(){busy.value=true;try{await collaboration.markAll()}catch(e){error.value=e.friendly}finally{busy.value=false}}
async function open(item){
  error.value=''
  try {
    if(workspace.dirty.value && !window.confirm('Leave this file? Your unsaved draft will remain in this browser session.'))return
    if(session.state.activeId!==item.team_id){session.selectTeam(item.team_id);await session.loadTeam();await projects.loadProjects()}
    if(projects.state.activeId!==item.project_id)await projects.select(item.project_id)
    await mark(item.id);collaboration.state.notificationDrawer=false
    if(item.node_id)await router.push({path:'/workspace',query:{file:item.node_id,task:item.task_id || undefined}})
    else {await router.push('/');if(item.task_id)projects.openTask(item.task_id)}
  }catch(e){error.value=e.friendly}
}
</script>
<template><div class="collaboration-controls"><button class="presence-trigger" aria-label="Show collaborators" @click="presence.toggle($event)"><Radio :size="14" :class="{online:collaboration.state.connected}"/><span>{{ collaboration.state.connected ? `${users.length} online` : collaboration.state.status }}</span></button><Popover ref="presence" class="presence-popover"><h3>Live collaborators</h3><p class="field-hint">{{ collaboration.state.connected ? 'Active connections in this project.' : 'Connection interrupted. Rejoining automatically.' }}</p><div v-for="(peer,index) in users" :key="`${peer.user.id}-${index}`" class="presence-person"><span class="avatar avatar-small">{{ initials(peer.user.name) }}</span><div><strong>{{ peer.user.name }}</strong><span>{{ peer.path ? `${peer.state} ${peer.path}` : 'Viewing this project' }}</span></div><i class="online-dot"></i></div><p v-if="!users.length" class="field-hint">No active collaborators.</p><p v-if="collaboration.state.error" class="form-error">{{ collaboration.state.error }}</p></Popover><button class="notification-trigger icon-button" aria-label="Open notifications" @click="collaboration.state.notificationDrawer=true;collaboration.notifications()"><Bell :size="18"/><span v-if="collaboration.state.unread" class="notification-count">{{ collaboration.state.unread }}</span></button></div><Drawer v-model:visible="collaboration.state.notificationDrawer" position="right" header="Notifications" class="notifications-drawer"><div class="notification-toolbar"><span>{{ collaboration.state.unread }} unread</span><Button label="Mark all read" text size="small" :disabled="!collaboration.state.unread" :loading="busy" @click="all"><template #icon><CheckCheck :size="15"/></template></Button></div><p v-if="error || collaboration.state.error" class="form-error" role="alert">{{ error || collaboration.state.error }}</p><article v-for="item in collaboration.state.notifications" :key="item.id" :class="['notification-item',{unread:!item.read}]"><button @click="open(item)"><strong>{{ item.message }}</strong><time>{{ timestamp(item.created_at) }}</time><ArrowUpRight :size="14"/></button><Button v-if="!item.read" text size="small" label="Mark read" @click="mark(item.id)"/></article><div v-if="!collaboration.state.notifications.length" class="compact-empty">You’re all caught up. Relevant updates will appear here.</div></Drawer></template>
