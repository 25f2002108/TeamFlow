<script setup>
import { ref, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { UserRound, Users, LogOut } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useRouter } from 'vue-router'
import { session } from '../../stores/session'
import { projects } from '../../stores/projects'
import { api } from '../../services/api'
const name = ref(session.state.user.name), teamName = ref(session.state.team.name), savingProfile = ref(false), savingTeam = ref(false), leaving = ref(false), error = ref('')
const toast = useToast(), confirm = useConfirm(), router = useRouter(), leader = computed(() => session.state.team.role === 'LEADER')
async function saveProfile() {
  savingProfile.value = true; error.value = ''
  try { session.state.user = (await api.patch('/users/me', { name: name.value })).data.user; name.value = session.state.user.name; await session.loadTeam(); await projects.refresh(); toast.add({ severity: 'success', summary: 'Profile saved', life: 3000 }) }
  catch (e) { error.value = e.friendly } finally { savingProfile.value = false }
}
async function saveTeam() {
  savingTeam.value = true; error.value = ''
  try { await api.patch(`/teams/${session.state.activeId}`, { name: teamName.value }); await session.loadTeam(); teamName.value = session.state.team.name; toast.add({ severity: 'success', summary: 'Team name updated', life: 3000 }) }
  catch (e) { error.value = e.friendly } finally { savingTeam.value = false }
}
function leave() { confirm.require({ header: 'Leave this team?', message: 'You will lose access to this team. You can join again with its invitation code.', acceptLabel: 'Leave team', rejectLabel: 'Stay', acceptProps: { severity: 'danger' }, accept: async () => {
  leaving.value = true
  try { await api.post(`/teams/${session.state.activeId}/leave`); await session.refresh(); router.push(session.state.teams.length ? '/' : '/onboarding'); toast.add({ severity: 'success', summary: 'You left the team', life: 3000 }) }
  catch (e) { error.value = e.friendly } finally { leaving.value = false }
} }) }
</script>
<template><div class="page-heading"><div><span class="eyebrow">YOUR WORKSPACE, YOUR WAY</span><h1>Settings</h1><p>The essentials for your account and team.</p></div></div><p v-if="error" class="form-error" role="alert">{{ error }}</p><section class="panel settings-panel"><div class="settings-intro"><span class="icon-box"><UserRound :size="20" /></span><div><h2>Your profile</h2><p>How your teammates see you.</p></div></div><form class="settings-form form-stack" @submit.prevent="saveProfile"><label for="display-name">Display name</label><InputText id="display-name" v-model="name" minlength="2" maxlength="80" required :disabled="savingProfile" /><label>Email address</label><p class="readonly-value">{{ session.state.user.email }}</p><p class="field-hint">Your email identifies your account and cannot be changed in this phase.</p><div class="form-actions"><Button type="submit" label="Save profile" :loading="savingProfile" :disabled="name.trim() === session.state.user.name" /></div></form></section><section class="panel settings-panel mt-4"><div class="settings-intro"><span class="icon-box"><Users :size="20" /></span><div><h2>Team settings</h2><p>{{ leader ? 'Manage the identity of your shared space.' : 'Managed by your team leader.' }}</p></div></div><form v-if="leader" class="settings-form form-stack" @submit.prevent="saveTeam"><label for="team-name">Team name</label><InputText id="team-name" v-model="teamName" minlength="2" maxlength="80" required :disabled="savingTeam" /><p class="field-hint">Updates for everyone on your team.</p><div class="form-actions"><Button type="submit" label="Save team name" :loading="savingTeam" :disabled="teamName.trim() === session.state.team.name" /></div><p class="field-hint mt-3">Leaders cannot leave or remove themselves. Leadership transfer will be added in a later phase.</p></form><div v-else class="settings-form"><p class="text-secondary">You belong to {{ session.state.team.name }} as a team member.</p><Button label="Leave team" severity="danger" outlined :loading="leaving" @click="leave"><template #icon><LogOut :size="16" /></template></Button></div></section></template>
