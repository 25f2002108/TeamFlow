<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Skeleton from 'primevue/skeleton'
import { Download, Paperclip, Trash2, MessageSquare, History } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { api } from '../../services/api'
import { projects } from '../../stores/projects'
import { session } from '../../stores/session'
import { initials, timestamp, size, activityText } from '../../utils/format'
import TaskFields from './TaskFields.vue'
import Dependencies from './Dependencies.vue'
import TaskConflict from './TaskConflict.vue'
import RelatedFiles from './RelatedFiles.vue'
const openedVersion=ref(null), openedBase=ref({}), conflict=ref(null), pendingChanges=ref({})
const editableKeys=['title','description','assigned_to','priority','deadline','status','progress','estimated_duration']
const detail = ref(null), form = reactive({}), loading = ref(false), busy = ref(false), commenting = ref(false), uploading = ref(false), deleting = ref(null), downloading = ref(null), error = ref(''), content = ref(''), fileInput = ref(), tab = ref('discussion')
const toast = useToast(), confirm = useConfirm(), leader = computed(() => session.state.team?.role === 'LEADER'), editable = computed(() => leader.value || detail.value?.task.assigned_to === session.state.user?.id)
const visible = computed({ get: () => !!projects.state.taskId, set: value => { if (!value) projects.state.taskId = null } })
let ticket = 0
async function load(resetForm=true) {
  const id = projects.state.taskId, version = ++ticket
  if (!id) return
  loading.value = true; error.value = ''
  try { const { data } = await api.get(`/tasks/${id}`); if (version !== ticket || id !== projects.state.taskId) return; const dirty=detail.value && editableKeys.some(key=>(form[key] || null)!==(openedBase.value[key] || null)); detail.value = data; if (resetForm || !dirty) {Object.assign(form, { ...data.task, deadline: data.task.deadline || '' });openedVersion.value=data.task.version;openedBase.value={...data.task}} }
  catch (e) { if (version === ticket) error.value = e.friendly } finally { if (version === ticket) loading.value = false }
}
watch(() => projects.state.taskId, id => { ticket++; detail.value = null; content.value = ''; error.value = ''; tab.value = 'discussion';conflict.value=null; if (id) load() })
function remote(){if(projects.state.taskId && !busy.value && !commenting.value && !uploading.value)load(false)}
onMounted(()=>window.addEventListener('teamflow-project-updated',remote))
onBeforeUnmount(()=>window.removeEventListener('teamflow-project-updated',remote))
async function save(merge=false, resolution=null) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    const keys=leader.value?editableKeys:['status','progress']
    const changes=resolution || Object.fromEntries(keys.filter(k=>(form[k] ?? null)!==(openedBase.value[k] ?? null)).map(k=>[k,k==='deadline'?form[k] || null:form[k]]))
    pendingChanges.value=changes
    const version=resolution?conflict.value.current.version:openedVersion.value
    await projects.patchTask({...detail.value.task,version},{...changes,...(merge?{merge:true}:{})});conflict.value=null;await load();toast.add({severity:'success',summary:'Task saved',life:3000})
  } catch (e) { error.value=e.friendly;if(e.response?.status===409 && e.response.data.current)conflict.value=e.response.data } finally { busy.value=false }
}
function useLatest(){if(window.confirm('Discard your task draft and load the latest task?')){conflict.value=null;load()}}
async function comment() {
  if (commenting.value || !content.value.trim()) return
  commenting.value = true; error.value = ''
  try { await api.post(`/tasks/${projects.state.taskId}/comments`, { content: content.value }); content.value = ''; await projects.refresh(); await load(false); toast.add({ severity: 'success', summary: 'Comment added', life: 2500 }) }
  catch (e) { error.value = e.friendly } finally { commenting.value = false }
}
async function upload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (file.size > 10*1024*1024) { error.value = 'Files must be 10 MB or smaller.'; event.target.value = ''; return }
  uploading.value = true; error.value = ''
  try { const body = new FormData(); body.append('file', file); await api.post(`/tasks/${projects.state.taskId}/attachments`, body); await projects.refresh(); await load(false); toast.add({ severity: 'success', summary: 'Attachment uploaded', life: 3000 }) }
  catch (e) { error.value = e.friendly } finally { uploading.value = false; event.target.value = '' }
}
async function download(item) {
  downloading.value = item.id
  try { const response = await api.get(`/tasks/${projects.state.taskId}/attachments/${item.id}`, { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const a = document.createElement('a'); a.href=url; a.download=item.filename; a.click(); setTimeout(()=>URL.revokeObjectURL(url), 1000) }
  catch (e) { toast.add({ severity: 'error', summary: e.friendly, life: 4500 }) } finally { downloading.value = null }
}
function remove(item) { const taskId = projects.state.taskId; confirm.require({ header: 'Delete attachment?', message: `${item.filename} will be deleted from this task.`, acceptLabel: 'Delete attachment', rejectLabel: 'Cancel', rejectProps: { severity: 'secondary' }, acceptProps: { severity: 'danger' }, accept: async () => {
  deleting.value=item.id
  try { await api.delete(`/tasks/${taskId}/attachments/${item.id}`); await projects.refresh(); await load(false); toast.add({ severity:'success',summary:'Attachment deleted',life:3000 }) } catch(e) { error.value=e.friendly } finally { deleting.value=null }
} }) }
</script>
<template><Drawer v-model:visible="visible" position="right" class="task-drawer" :header="detail ? `Task TF-${detail.task.id}` : 'Task details'" :dismissable="!busy && !uploading && !commenting" :closeOnEscape="!busy && !uploading && !commenting"><div v-if="loading && !detail"><Skeleton height="45px" /><Skeleton class="mt-3" height="200px" /></div><p v-if="error" class="form-error mb-3" role="alert">{{ error }}</p><Button v-if="!detail && error" label="Retry" severity="secondary" @click="load()" /><template v-if="detail"><div class="drawer-kicker"><span class="eyebrow">{{ projects.active.value?.name }}</span><span>Version {{ detail.task.version }}</span></div><form @submit.prevent="save()"><TaskFields :modelValue="form" :leader="leader" :editable="editable" :busy="busy || projects.state.busy" /><div class="form-actions d-flex justify-content-between align-items-center"><span class="field-hint">{{ editable ? 'Changes are saved explicitly.' : 'Only the assignee or leader can edit work fields.' }}</span><Button v-if="editable" type="submit" label="Save changes" :loading="busy" :disabled="projects.state.busy" /></div></form><TaskConflict v-if="conflict" :conflict="conflict" :changes="pendingChanges" :busy="busy" @merge="save(true)" @latest="useLatest" @resolve="save(false,$event)"/><Dependencies :task="detail.task" @changed="load(false)"/><RelatedFiles :task="detail.task" @changed="load(false)" /><div class="drawer-tabs" role="tablist" aria-label="Task collaboration"><button :class="{ active: tab === 'discussion' }" role="tab" :aria-selected="tab === 'discussion'" @click="tab = 'discussion'"><MessageSquare :size="15" /> Discussion <span>{{ detail.comments.length }}</span></button><button :class="{ active: tab === 'attachments' }" role="tab" :aria-selected="tab === 'attachments'" @click="tab = 'attachments'"><Paperclip :size="15" /> Files <span>{{ detail.attachments.length }}</span></button><button :class="{ active: tab === 'history' }" role="tab" :aria-selected="tab === 'history'" @click="tab = 'history'"><History :size="15" /> History</button></div><section v-if="tab === 'discussion'" role="tabpanel"><div v-if="!detail.comments.length" class="compact-empty">Start the conversation. Context belongs with the work.</div><article v-for="item in detail.comments" :key="item.id" class="comment"><span class="avatar avatar-small">{{ initials(item.author.name) }}</span><div><div class="comment-meta"><strong>{{ item.author.name }}</strong><time>{{ timestamp(item.created_at) }}</time></div><p>{{ item.content }}</p></div></article><form class="comment-composer form-stack" @submit.prevent="comment"><label for="comment-content">Add a comment</label><Textarea id="comment-content" v-model="content" rows="3" maxlength="5000" required :disabled="commenting" placeholder="Share an update or ask a question…" /><Button type="submit" label="Post comment" :loading="commenting" :disabled="!content.trim()" /></form></section><section v-else-if="tab === 'attachments'" role="tabpanel"><div class="attachment-header"><div><h3>Supporting files</h3><p>PDF, images, text, Office documents or ZIP. Up to 10 MB.</p></div><Button label="Upload" severity="secondary" :loading="uploading" @click="fileInput.click()"><template #icon><Paperclip :size="15" /></template></Button><input ref="fileInput" type="file" class="visually-hidden" tabindex="-1" aria-label="Upload attachment" accept=".txt,.md,.csv,.json,.pdf,.png,.jpg,.jpeg,.webp,.docx,.xlsx,.pptx,.zip" @change="upload" /></div><div v-if="!detail.attachments.length" class="compact-empty">No supporting files yet.</div><article v-for="item in detail.attachments" :key="item.id" class="attachment-row"><Paperclip :size="18" /><div><strong>{{ item.filename }}</strong><span>{{ size(item.size) }} · {{ item.author.name }} · {{ timestamp(item.created_at) }}</span></div><Button :aria-label="`Download ${item.filename}`" severity="secondary" text :loading="downloading === item.id" @click="download(item)"><Download :size="16" /></Button><Button v-if="leader || item.author.id === session.state.user.id" :aria-label="`Delete ${item.filename}`" severity="danger" text :loading="deleting === item.id" @click="remove(item)"><Trash2 :size="16" /></Button></article></section><section v-else role="tabpanel"><p class="field-hint mb-3">Latest 50 events for this task.</p><div v-for="item in detail.activity" :key="item.id" class="history-row"><span class="activity-dot"></span><div><p><strong>{{ item.actor.name }}</strong> {{ activityText(item) }}</p><time>{{ timestamp(item.created_at) }}</time></div></div></section></template></Drawer></template>


