<script setup>
import Skeleton from 'primevue/skeleton'
import Button from 'primevue/button'
import ProjectEmpty from './ProjectEmpty.vue'
import { projects } from '../../stores/projects'
async function retry() { try { if (projects.state.activeId) await projects.refresh(); else await projects.loadProjects() } catch {} }
</script>
<template><section v-if="projects.state.error" class="panel error-panel" role="alert"><h2>Project data couldn’t be loaded.</h2><p>{{ projects.state.error }}</p><Button label="Retry" @click="retry" /></section><div v-else-if="projects.state.loading && !projects.state.dashboard" aria-label="Loading project"><Skeleton height="50px" width="50%" /><Skeleton class="mt-4" height="280px" /></div><ProjectEmpty v-else-if="!projects.state.activeId" /><slot v-else /></template>
