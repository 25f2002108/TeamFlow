<script setup>
import { projects } from '../../stores/projects'
import { initials, timestamp, activityText } from '../../utils/format'
defineProps({ items: Array, compact: Boolean })
</script>
<template><div class="activity-list"><article v-for="item in items" :key="item.id" class="activity-row"><span class="avatar avatar-small">{{ initials(item.actor.name) }}</span><div><p><strong>{{ item.actor.name }}</strong> {{ activityText(item) }}</p><time>{{ timestamp(item.created_at) }}</time></div><button v-if="item.entity_type==='task'" class="activity-open" :aria-label="`Open task ${item.details.title}`" @click="projects.openTask(item.entity_id)">TF-{{ item.entity_id }}</button></article><div v-if="!items?.length" class="compact-empty">Project activity will appear as your team works.</div></div></template>
