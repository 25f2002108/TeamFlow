<script setup>
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { api } from '../../services/api'
import { session } from '../../stores/session'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
const props = defineProps({ mode: { type: String, default: 'create' } })
const emit = defineEmits(['done'])
const value = ref(''), busy = ref(false), error = ref(''), router = useRouter(), toast = useToast()
async function submit() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    const { data } = await api.post(props.mode === 'create' ? '/teams' : '/teams/join', props.mode === 'create' ? { name: value.value } : { team_code: value.value })
    await session.refresh(); session.selectTeam(data.team.id); emit('done'); await router.push('/')
    toast.add({ severity: 'success', summary: props.mode === 'create' ? 'Team created' : 'Welcome to the team', detail: data.team.name, life: 3500 })
  } catch (e) { error.value = e.friendly } finally { busy.value = false }
}
</script>
<template><form @submit.prevent="submit" class="form-stack"><label for="team-value">{{ mode === 'create' ? 'Team name' : 'Team code' }}</label><InputText id="team-value" v-model="value" :placeholder="mode === 'create' ? 'e.g. Studio North' : 'TF-XXXXXX'" :minlength="mode === 'create' ? 2 : 4" :maxlength="mode === 'create' ? 80 : 20" required :disabled="busy" autofocus /><p class="field-hint">{{ mode === 'create' ? 'Give your team a name. You can change it later.' : 'Ask your team leader for an invitation code.' }}</p><p v-if="error" class="form-error" role="alert">{{ error }}</p><Button type="submit" :loading="busy" :label="busy ? mode === 'create' ? 'Creating team…' : 'Joining team…' : mode === 'create' ? 'Create team' : 'Join team'" /></form></template>
