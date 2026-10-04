<script setup>
import { ref } from 'vue'
import Button from 'primevue/button'
import { RefreshCw } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { projects } from '../../stores/projects'
import { api } from '../../services/api'
import ActivityList from '../../components/common/ActivityList.vue'
import ProjectState from '../../components/project/ProjectState.vue'
const more=ref(false), toast=useToast()
async function loadMore() {
  more.value=true
  const id=projects.state.activeId
  try { const {data}=await api.get(`/projects/${id}/activity`,{params:{offset:projects.state.activity.length}}); if(id===projects.state.activeId) { projects.state.activity.push(...data.activity); projects.state.hasMore=data.has_more } }
  catch(e) { toast.add({severity:'error',summary:e.friendly,life:4000}) } finally { more.value=false }
}
async function refresh() { try { await projects.refresh() } catch(e) { toast.add({severity:'error',summary:e.friendly,life:4000}) } }
</script>
<template><ProjectState><div class="page-heading"><div><span class="eyebrow">THE STORY OF YOUR WORK</span><h1>Activity</h1><p>A shared record of what changed, who changed it, and when.</p></div><Button label="Refresh" severity="secondary" :loading="projects.state.loading" @click="refresh"><template #icon><RefreshCw :size="16" /></template></Button></div><section class="panel activity-panel"><ActivityList :items="projects.state.activity" /><Button v-if="projects.state.hasMore" label="Load more" severity="secondary" :loading="more" @click="loadMore" /></section></ProjectState></template>
