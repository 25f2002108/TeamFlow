<script setup>
import { ref } from 'vue'
import Button from 'primevue/button'
import { Copy, Check, KeyRound } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
defineProps({ code: String })
const toast = useToast(), copied = ref(false)
async function copy(code) {
  try { await navigator.clipboard.writeText(code); copied.value = true; toast.add({ severity: 'success', summary: 'Team code copied', detail: 'Share it with someone you want to invite.', life: 3000 }); setTimeout(() => copied.value = false, 2500) }
  catch { toast.add({ severity: 'error', summary: 'Clipboard unavailable', detail: 'Select and copy the team code manually.', life: 5000 }) }
}
</script>
<template><section class="invite-card"><div class="icon-box"><KeyRound :size="19" /></div><div><h3>Your team, one code away.</h3><p>Share this code to invite a teammate. Anyone with it can join.</p></div><div class="code-row"><code>{{ code }}</code><Button :aria-label="copied ? 'Code copied' : 'Copy team code'" severity="secondary" @click="copy(code)"><Check v-if="copied" :size="16" /><Copy v-else :size="16" />{{ copied ? 'Copied' : 'Copy code' }}</Button></div></section></template>
