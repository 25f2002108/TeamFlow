<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { development as dev } from '../../stores/development'
import { session } from '../../stores/session'
const host=ref(),command=ref(''),hiddenUntil=ref(0)
let terminal,fit,observer,poll,shown='',executionId=null
function render(){if(!terminal)return;const item=dev.state.execution; if(item?.id!==executionId){executionId=item?.id;hiddenUntil.value=0;shown='';terminal.reset()}
 const output=(item?.output || '').slice(hiddenUntil.value);if(!output.startsWith(shown)){terminal.reset();shown=''};if(output.length>shown.length)terminal.write(output.slice(shown.length).replace(/\r?\n/g,'\r\n'));shown=output}
function clear(){hiddenUntil.value=dev.state.execution?.output.length || 0;shown='';terminal?.reset()}
onMounted(async()=>{terminal=new Terminal({theme:{background:'#f1f6f5',foreground:'#243b40',cursor:'#0f817b',selectionBackground:'#b9e4dc'},fontFamily:'Consolas, monospace',fontSize:12,convertEol:true,disableStdin:true,scrollback:3000,allowProposedApi:false});fit=new FitAddon();terminal.loadAddon(fit);terminal.open(host.value);observer=new ResizeObserver(()=>fit.fit());observer.observe(host.value);render();poll=setInterval(()=>{if(dev.state.execution?.status==='running')dev.poll()},1500)})
watch(()=>[dev.state.execution?.id,dev.state.execution?.output],render)
onBeforeUnmount(()=>{clearInterval(poll);observer?.disconnect();terminal?.dispose()})
</script>
<template><section class="terminal-panel"><header><strong>Terminal</strong><span v-if="dev.state.execution">{{ dev.state.execution.kind }} · {{ dev.state.execution.status }}<template v-if="dev.state.execution.exit_code!==null"> · Exit {{ dev.state.execution.exit_code }}</template></span><span class="terminal-spacer"></span><Button v-if="dev.state.execution?.status==='running' && (dev.state.execution.user_id===session.state.user.id || session.state.team.role==='LEADER')" label="Stop process" severity="danger" text @click="dev.stop"/><Button label="Clear terminal" text @click="clear"/><Button label="Collapse" text @click="dev.state.terminal=false"/></header><p v-if="dev.state.error" role="alert" class="form-error">{{ dev.state.error }}</p><p v-if="dev.state.execution" class="terminal-command">$ {{ dev.state.execution.command }}</p><div ref="host" class="terminal-output" aria-label="Process output"></div><form class="terminal-input" @submit.prevent="dev.start('terminal',command)"><label for="terminal-command">$</label><InputText id="terminal-command" v-model="command" placeholder="python app.py" aria-label="Terminal command" :disabled="dev.state.busy || dev.state.execution?.status==='running'"/><Button label="Execute" type="submit" :loading="dev.state.busy" :disabled="!command.trim() || dev.state.execution?.status==='running'"/></form><small>Fresh saved workspace · Python commands · 120-second limit · trusted local code only</small></section></template>
