<script setup>
import { computed, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Slider from 'primevue/slider'
import { session } from '../../stores/session'
import { statuses, priorities } from '../../utils/format'
const form = defineModel({ required: true })
const props = defineProps({ leader: Boolean, editable: Boolean, busy: Boolean })
const members = computed(() => [{ name: 'Unassigned', id: null }, ...session.state.members])
watch(() => form.value.status, (status, old) => { if (status === 'DONE') form.value.progress = 100; else if (old === 'DONE' && form.value.progress === 100) form.value.progress = 0 })
watch(() => form.value.progress, progress => { if (progress === 100) form.value.status = 'DONE'; else if (form.value.status === 'DONE') form.value.status = 'IN_PROGRESS' })
</script>
<template><div class="form-stack task-fields"><label for="task-title">Title</label><InputText id="task-title" v-model="form.title" minlength="2" maxlength="180" required :disabled="!leader || busy" /><label for="task-description">Description</label><Textarea id="task-description" v-model="form.description" rows="4" maxlength="10000" :disabled="!leader || busy" /><div class="row g-3"><div class="col-sm-6 form-stack"><label for="task-assignee">Assignee</label><Select inputId="task-assignee" aria-label="Assignee" placeholder="Unassigned" v-model="form.assigned_to" :options="members" optionLabel="name" optionValue="id" :disabled="!leader || busy" filter appendTo="self" /></div><div class="col-sm-6 form-stack"><label for="task-priority">Priority</label><Select inputId="task-priority" aria-label="Priority" v-model="form.priority" :options="priorities" optionLabel="label" optionValue="value" :disabled="!leader || busy" appendTo="self" /></div><div class="col-sm-6 form-stack"><label for="task-deadline">Deadline</label><InputText id="task-deadline" v-model="form.deadline" type="date" :disabled="!leader || busy" /></div><div class="col-sm-6 form-stack"><label for="task-status">Status</label><Select inputId="task-status" aria-label="Status" v-model="form.status" :options="statuses" optionLabel="label" optionValue="value" :disabled="!editable || busy" appendTo="self" /></div></div><div v-if="leader" class="form-stack"><label for="task-duration">Estimated duration (working days)</label><InputNumber inputId="task-duration" v-model="form.estimated_duration" :min="0.25" :max="365" :maxFractionDigits="2" :disabled="busy"/><small class="field-hint">Used for critical-path planning. Default: 1 day.</small></div><div class="progress-editor"><label for="task-progress">Progress</label><InputNumber inputId="task-progress" v-model="form.progress" :min="0" :max="100" :maxFractionDigits="0" suffix="%" :disabled="!editable || busy" /><Slider v-model="form.progress" :min="0" :max="100" :step="1" :disabled="!editable || busy" aria-label="Task progress" /></div><p class="field-hint">Save to apply changes. Done means 100%; reopening a completed task resets progress to 0%.</p></div></template>
