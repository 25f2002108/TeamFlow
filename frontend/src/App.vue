<script setup>
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'
import { session } from './stores/session'
import { useRouter } from 'vue-router'
const router = useRouter()
async function retry() { await session.restore(); if (!session.state.error) router.replace(session.state.user ? session.state.teams.length ? '/' : '/onboarding' : '/login') }
</script>
<template>
  <Toast position="top-right" /><ConfirmDialog />
  <div v-if="!session.state.ready" class="initial-loading" aria-label="Loading TeamFlow"><div class="brand mb-4"><span class="brand-mark">T</span> TeamFlow</div><Skeleton width="280px" height="16px" /><Skeleton class="mt-3" width="200px" height="16px" /></div>
  <div v-else-if="session.state.error" class="initial-loading"><h1>Unable to connect</h1><p role="alert">{{ session.state.error }}</p><Button label="Try again" @click="retry" /></div>
  <RouterView v-else />
</template>
