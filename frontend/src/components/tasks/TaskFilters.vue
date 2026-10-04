<script setup>
import { computed } from 'vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import { Search, SlidersHorizontal, X } from 'lucide-vue-next'
import { statuses, priorities } from '../../utils/format'
import { session } from '../../stores/session'
const filters=defineModel({required:true})
defineProps({ assignee: Boolean })
defineEmits(['clear'])
const members=computed(()=>[{name:'All assignees',id:''},{name:'Unassigned',id:'none'},...session.state.members])
const statusOptions=[{label:'All statuses',value:''},...statuses], priorityOptions=[{label:'All priorities',value:''},...priorities]
const dueOptions=[{label:'Any deadline',value:''},...['Overdue','Due today','Due soon','Upcoming','Completed','No deadline'].map(value=>({label:value,value}))]
const sortOptions=[{label:'Recently updated',value:'updated'},{label:'Deadline',value:'deadline'},{label:'Priority',value:'priority'},{label:'Progress',value:'progress'}]
</script>
<template><div class="task-filters"><div class="search-box"><Search :size="16" /><InputText v-model="filters.query" placeholder="Search tasks…" aria-label="Search tasks" /></div><Select v-model="filters.status" :options="statusOptions" optionLabel="label" optionValue="value" aria-label="Filter status" placeholder="All statuses" /><Select v-model="filters.priority" :options="priorityOptions" optionLabel="label" optionValue="value" aria-label="Filter priority" placeholder="All priorities" /><Select v-if="assignee" v-model="filters.assignee" :options="members" optionLabel="name" optionValue="id" aria-label="Filter assignee" placeholder="All assignees" /><Select v-model="filters.due" :options="dueOptions" optionLabel="label" optionValue="value" aria-label="Filter deadline" placeholder="Any deadline" /><div class="filter-sort"><SlidersHorizontal :size="14" /><Select v-model="filters.sort" :options="sortOptions" optionLabel="label" optionValue="value" aria-label="Sort tasks" /></div><Button label="Clear" severity="secondary" text size="small" @click="$emit('clear')"><template #icon><X :size="13" /></template></Button></div></template>
