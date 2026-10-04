<script setup>
import { FolderKanban, Plus } from 'lucide-vue-next'
import Button from 'primevue/button'
import { session } from '../../stores/session'
import { projects } from '../../stores/projects'
</script>
<template><section class="project-empty panel"><div class="empty-orbit"><FolderKanban :size="32" /></div><span class="eyebrow">ROOM FOR YOUR NEXT IDEA</span><h1>Start with a project.</h1><p>{{ session.state.team?.role === 'LEADER' ? 'Turn a shared goal into clear, connected work. Create your first project to start assigning tasks.' : 'Your team leader hasn’t created a project yet. Once they do, your shared work will appear here.' }}</p><Button v-if="session.state.team?.role === 'LEADER'" label="Create project" @click="projects.newProject"><template #icon><Plus :size="17" /></template></Button></section></template>
