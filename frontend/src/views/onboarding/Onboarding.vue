<script setup>
import { ref } from 'vue'
import { Users, Plus, ArrowRight, LogOut } from 'lucide-vue-next'
import Button from 'primevue/button'
import { session } from '../../stores/session'
import TeamForm from '../../components/team/TeamForm.vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
const mode = ref('create'), router = useRouter(), toast = useToast(), busy = ref(false)
async function logout() { busy.value = true; try { await session.logout(); router.push('/login') } catch (e) { toast.add({ severity: 'error', summary: e.friendly, life: 4000 }) } finally { busy.value = false } }
</script>
<template><div class="onboarding"><header class="onboarding-header"><div class="brand"><span class="brand-mark">T</span>TeamFlow</div><Button severity="secondary" text label="Sign out" :loading="busy" @click="logout"><template #icon><LogOut :size="16" /></template></Button></header><main class="onboarding-main"><span class="eyebrow">YOUR FIRST STEP</span><h1>A home for your team.</h1><p class="text-secondary">Welcome, {{ session.state.user.name }}. Create a new team or join the people already here.</p><div class="onboarding-options" role="group" aria-label="Team onboarding"><button :class="['option', { selected: mode === 'create' }]" @click="mode = 'create'"><Plus :size="23" /><strong>Create a team</strong><span>Start a space of your own.</span><ArrowRight :size="17" /></button><button :class="['option', { selected: mode === 'join' }]" @click="mode = 'join'"><Users :size="23" /><strong>Join a team</strong><span>Use an invitation code.</span><ArrowRight :size="17" /></button></div><section class="panel onboarding-panel"><h2>{{ mode === 'create' ? 'Set up your team' : 'Find your team' }}</h2><TeamForm :key="mode" :mode="mode" /></section><p class="onboarding-footnote">One account. Multiple teams. Switch between them anytime.</p></main></div></template>
