<script setup>
import { computed, reactive } from 'vue'
import Button from 'primevue/button'
const props=defineProps({conflict:Object,changes:Object,busy:Boolean}),emit=defineEmits(['merge','latest','resolve'])
const choices=reactive({})
const rows=computed(()=>Object.keys(props.changes).filter(k=>k!=='merge'))
function resolve(){const changes={};for(const key of rows.value){if(!props.conflict.conflicts.includes(key) || choices[key]==='mine')changes[key]=props.changes[key]}emit('resolve',changes)}
function display(value){return value===null || value===''?'None':String(value)}
</script>
<template><section class="task-conflict" role="alert"><span class="eyebrow">CONFLICT DETECTED</span><h3>Review your changes and team changes</h3><p>Your draft has been kept. Current version: {{ conflict.current.version }}.</p><div v-for="key in rows" :key="key" class="conflict-field"><strong>{{ key.replaceAll('_',' ') }}</strong><span>Your value: {{ display(changes[key]) }}</span><span>Team value: {{ display(conflict.current[key]) }}</span><label v-if="conflict.conflicts.includes(key)">Resolution<select v-model="choices[key]" :aria-label="`Resolve ${key}`"><option :value="undefined">Use team value</option><option value="mine">Use my value</option></select></label><small v-else>Safe to merge</small></div><div class="conflict-actions"><Button label="Use latest" severity="secondary" @click="emit('latest')"/><Button v-if="conflict.base && !conflict.conflicts.length" label="Merge safe changes" :loading="busy" @click="emit('merge')"/><Button v-else label="Save reviewed resolution" :loading="busy" @click="resolve"/></div></section></template>
