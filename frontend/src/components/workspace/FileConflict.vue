<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import * as monaco from 'monaco-editor/editor/editor.api'
import { workspace } from '../../stores/workspace'
const visible=ref(false),host=ref(),busy=ref(false),error=ref('')
let editor,original,modified,version
function dispose(){editor?.dispose();original?.dispose();modified?.dispose();editor=null}
async function open(){visible.value=true;error.value='';await nextTick();setTimeout(()=>{if(!visible.value || !host.value)return;dispose();version=workspace.state.conflict.version;original=monaco.editor.createModel(workspace.state.conflict.content || '','plaintext');modified=monaco.editor.createModel(workspace.state.text,'plaintext');editor=monaco.editor.createDiffEditor(host.value,{theme:'teamflow-light',automaticLayout:true,originalEditable:false,readOnly:false,minimap:{enabled:false},renderSideBySide:window.innerWidth>700,wordWrap:'on'});editor.setModel({original,modified})},100)}
async function save(){if(!editor)return;busy.value=true;error.value='';workspace.state.version=version;workspace.state.base=original.getValue();workspace.edit(modified.getValue());if(!workspace.dirty.value || await workspace.save()){workspace.draft();visible.value=false;await workspace.refresh()}else error.value=workspace.state.error;busy.value=false}
function accept(){if(!window.confirm('Discard your local draft and accept the current TeamFlow version?'))return;workspace.state.text=workspace.state.base;workspace.open(workspace.state.active.id);visible.value=false}
watch(visible,value=>{if(!value)dispose()});onBeforeUnmount(dispose)
</script>
<template><div v-if="workspace.state.conflict" class="workspace-conflict" role="alert"><strong>File conflict — your draft is preserved.</strong><span>Review the saved TeamFlow version beside your changes and edit the merged result.</span><Button label="Review and resolve" size="small" @click="open"/><Button label="Download draft" severity="secondary" size="small" @click="workspace.downloadDraft"/></div><Dialog v-model:visible="visible" modal header="Resolve file conflict" :style="{width:'1100px'}" :breakpoints="{'1150px':'96vw'}" :closable="!busy"><div class="diff-labels"><strong>TeamFlow version</strong><strong>Your editable result</strong></div><div ref="host" class="conflict-diff"></div><p v-if="error" role="alert" class="form-error">{{ error }}</p><div class="conflict-actions"><Button label="Accept TeamFlow version" severity="secondary" @click="accept"/><Button label="Save merged result" :loading="busy" @click="save"/></div><p class="field-hint">Saving writes the right-hand result against the reviewed version. A newer team save triggers another conflict.</p></Dialog></template>
