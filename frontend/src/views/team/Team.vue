<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { Search, UserMinus, Users, RefreshCw } from 'lucide-vue-next'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { api } from '../../services/api'
import { session } from '../../stores/session'
import { projects } from '../../stores/projects'
import { collaboration } from '../../stores/collaboration'
import CodeCard from '../../components/common/CodeCard.vue'
const route = useRoute(), search = ref(String(route.query.search || '')), busy = ref(false), removing = ref(null), confirm = useConfirm(), toast = useToast()
watch(() => route.query.search, value => search.value = String(value || ''))
const members = computed(() => session.state.members.filter(m => `${m.name} ${m.email}`.toLowerCase().includes(search.value.toLowerCase())))
const leader = computed(() => session.state.team.role === 'LEADER')
async function refresh() { busy.value = true; try { await session.loadTeam() } catch (e) { toast.add({ severity: 'error', summary: e.friendly, life: 4500 }) } finally { busy.value = false } }
function remove(member) { confirm.require({ header: 'Remove team member?', message: `${member.name} will lose access to ${session.state.team.name}. They can rejoin with an invitation code.`, rejectLabel: 'Cancel', acceptLabel: 'Remove member', acceptProps: { severity: 'danger' }, accept: async () => {
  removing.value = member.id
  try { await api.delete(`/teams/${session.state.activeId}/members/${member.id}`); await session.loadTeam(); if (projects.state.activeId) await projects.refresh(); toast.add({ severity: 'success', summary: 'Member removed', life: 3000 }) }
  catch (e) { toast.add({ severity: 'error', summary: e.friendly, life: 4500 }) } finally { removing.value = null }
} }) }
const date = value => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
</script>
<template><div class="page-heading"><div><span class="eyebrow">THE PEOPLE</span><h1>Your team</h1><p>{{ session.state.team.member_count }} {{ session.state.team.member_count === 1 ? 'person' : 'people' }} building a shared foundation.</p></div><Button label="Refresh" severity="secondary" :loading="busy" @click="refresh"><template #icon><RefreshCw :size="16" /></template></Button></div><CodeCard v-if="leader" :code="session.state.team.team_code" /><section class="panel members-panel mt-4"><div class="members-toolbar"><h2>Members <span class="count-badge">{{ session.state.members.length }}</span></h2><div class="search-box"><Search :size="16" /><InputText v-model="search" aria-label="Search members" placeholder="Search name or email" /></div></div><div class="member-table-head"><span>NAME</span><span>ROLE</span><span>JOINED</span><span></span></div><article v-for="member in members" :key="member.id" class="member-row"><div class="member-identity"><span class="avatar">{{ member.name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase() }}</span><div><strong>{{ member.name }}<span v-if="member.id === session.state.user.id" class="you-label">you</span></strong><span>{{ member.email }}</span><span :class="['member-presence',{online:collaboration.state.users.some(peer=>peer.user.id===member.id)}]">{{ collaboration.state.connected ? collaboration.state.users.some(peer=>peer.user.id===member.id)?'Online':'Offline':'Presence unavailable' }}</span></div></div><span :class="['role-badge', { leader: member.role === 'LEADER' }]">{{ member.role === 'LEADER' ? 'Leader' : 'Member' }}</span><span class="joined-date">{{ date(member.joined_at) }}</span><Button v-if="leader && member.role === 'MEMBER'" :aria-label="`Remove ${member.name}`" severity="danger" text :loading="removing === member.id" :disabled="removing !== null" @click="remove(member)"><UserMinus :size="17" /></Button></article><div v-if="!members.length" class="empty-state"><Search :size="27" /><h3>No matching teammates</h3><p>Try a different name or email address.</p><Button label="Clear search" severity="secondary" @click="search = ''" /></div><div v-else-if="session.state.members.length === 1" class="empty-state invite-empty"><Users :size="28" /><h3>A team starts with you.</h3><p>{{ leader ? 'Share your team code above to welcome your first teammate.' : 'Your team is still getting started.' }}</p></div></section><p class="section-note">Membership and presence update live while connected.</p></template>

