<script setup>
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Button from 'primevue/button'
import { api } from '../../services/api'
import { workspace } from '../../stores/workspace'
const node=defineModel(), rows=ref([]), busy=ref(false),loading=ref(false),error=ref('')
const options=[{label:'Inherit',value:null},...['VIEW','EDIT','NO_ACCESS','FULL_ACCESS'].map(value=>({label:value.replaceAll('_',' '),value}))]
watch(node,async value=>{error.value='';rows.value=[];if(!value)return;loading.value=true;try{rows.value=(await api.get(`/workspace/nodes/${value.id}/permissions`)).data.members}catch(e){error.value=e.friendly}finally{loading.value=false}})
async function save(){busy.value=true;try{await api.put(`/workspace/nodes/${node.value.id}/permissions`,{permissions:rows.value.filter(r=>r.role!=='LEADER').map(r=>({user_id:r.user.id,permission:r.permission}))});await workspace.refresh();node.value=null}catch(e){error.value=e.friendly}finally{busy.value=false}}
</script>
<template><Dialog :visible="!!node" modal header="Workspace permissions" :style="{width:'610px'}" :breakpoints="{'680px':'94vw'}" :closable="!busy" @update:visible="value=>{if(!value)node=null}"><p class="permission-path">{{ node?.path }}</p><p class="field-hint">Default: View. The nearest explicit rule applies; a No access ancestor blocks every descendant. Leaders always have full access.</p><p class="field-hint">View: read and discuss · Edit: also save content · Full access: also create, rename and delete nodes. Only leaders change permissions and task links.</p><p v-if="error" class="form-error" role="alert">{{ error }}</p><p v-if="loading" class="compact-empty">Loading current access…</p><div v-for="row in rows" :key="row.user.id" class="permission-row"><div><strong>{{ row.user.name }}</strong><span>{{ row.role==='LEADER'?'Leader · Full access':`Currently ${row.effective.replaceAll('_',' ').toLowerCase()}` }}</span></div><Select v-if="row.role!=='LEADER'" v-model="row.permission" :options="options" optionLabel="label" optionValue="value" placeholder="Inherit" :aria-label="`Permission for ${row.user.name}`" :disabled="busy"/></div><div class="form-actions"><Button label="Save permissions" :loading="busy" :disabled="loading || !rows.length" @click="save"/></div></Dialog></template>
