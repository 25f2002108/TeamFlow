<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as monaco from 'monaco-editor/editor/editor.api'
import EditorWorker from 'monaco-editor/editor/editor.worker?worker'
import 'monaco-editor/languages/definitions/python/register'
import 'monaco-editor/languages/definitions/javascript/register'
import 'monaco-editor/languages/definitions/typescript/register'
import 'monaco-editor/languages/definitions/html/register'
import 'monaco-editor/languages/definitions/css/register'
import 'monaco-editor/languages/definitions/markdown/register'
import 'monaco-editor/languages/definitions/yaml/register'
import 'monaco-editor/languages/features/json/register'
import 'monaco-editor/features/caretOperations/register'
import 'monaco-editor/features/clipboard/register'
import 'monaco-editor/features/find/register'
import 'monaco-editor/features/hover/register'
import 'monaco-editor/features/contextmenu/register'
import 'monaco-editor/features/folding/register'
import 'monaco-editor/features/comment/register'
import 'monaco-editor/features/indentation/register'
import 'monaco-editor/features/bracketMatching/register'
import JsonWorker from 'monaco-editor/languages/features/json/json.worker?worker'
const props=defineProps({node:Object,text:String,readonly:Boolean,comments:Array,peers:Array})
const emit=defineEmits(['change','save','selection','focus','blur','comment-line'])
const host=ref();let editor,model,ignore=false,decorations,observer
self.MonacoEnvironment={getWorker:(_,label)=>label==='json'?new JsonWorker():new EditorWorker()}
function language(name){return ({py:'python',js:'javascript',mjs:'javascript',ts:'typescript',vue:'html',json:'json',md:'markdown',css:'css',html:'html',yml:'yaml',yaml:'yaml'})[name.split('.').pop().toLowerCase()] || 'plaintext'}
function markers(){if(!editor || !model)return;const lines=model.getLineCount();decorations.set([...(props.comments || []).filter(c=>!c.resolved && c.line_start<=lines).map(c=>({range:new monaco.Range(c.line_start,1,c.line_start,1),options:{glyphMarginClassName:'code-comment-marker',glyphMarginHoverMessage:{value:`Discussion on line ${c.line_start} · saved version ${c.file_version}`}}})),...(props.peers || []).filter(p=>p.cursor && p.cursor.line<=lines).map(p=>({range:new monaco.Range(p.cursor.line,p.cursor.column,p.cursor.line,p.cursor.column),options:{beforeContentClassName:'remote-cursor',hoverMessage:{value:p.user.name.replace(/[\[\]()*_`]/g,'')}}}))])}
onMounted(()=>{
  monaco.editor.defineTheme('teamflow-light',{base:'vs',inherit:true,rules:[],colors:{'editor.background':'#fdfefd','editor.foreground':'#26324A','editor.lineHighlightBackground':'#edf7f1','editor.selectionBackground':'#bce8de','editorCursor.foreground':'#0f817b','editorLineNumber.foreground':'#8B93A7','editorLineNumber.activeForeground':'#0f817b','editorGutter.background':'#fdfefd'}})
  model=monaco.editor.createModel(props.text,language(props.node.name),monaco.Uri.parse(`inmemory://teamflow/${props.node.project_id}/${props.node.id}/${props.node.name}`))
  editor=monaco.editor.create(host.value,{model,theme:'teamflow-light',readOnly:props.readonly,automaticLayout:true,minimap:{enabled:false},fontSize:13,fontFamily:'Consolas, ui-monospace, monospace',lineHeight:22,glyphMargin:true,scrollBeyondLastLine:false,padding:{top:18,bottom:18},tabSize:2,wordWrap:'on',ariaLabel:`Code editor ${props.node.name}`,renderLineHighlight:'line',fixedOverflowWidgets:true})
  decorations=editor.createDecorationsCollection([]);markers()
  editor.onDidChangeModelContent(()=>{if(!ignore)emit('change',model.getValue())})
  editor.onDidChangeCursorSelection(e=>emit('selection',{line_start:e.selection.startLineNumber,line_end:e.selection.endLineNumber,cursor:{line:e.selection.positionLineNumber,column:e.selection.positionColumn}}))
  editor.onDidFocusEditorText(()=>emit('focus'));editor.onDidBlurEditorText(()=>emit('blur'))
  editor.onMouseDown(e=>{if(e.target.type===monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN && e.target.position)emit('comment-line',e.target.position.lineNumber)})
  editor.addCommand(monaco.KeyMod.CtrlCmd|monaco.KeyCode.KeyS,()=>emit('save'))
})
watch(()=>props.text,value=>{if(model && value!==model.getValue()){ignore=true;const selection=editor.getSelection();model.setValue(value);editor.setSelection(selection);ignore=false}})
watch(()=>props.readonly,value=>editor?.updateOptions({readOnly:value}))
watch(()=>props.node.name,value=>{if(model)monaco.editor.setModelLanguage(model,language(value))})
watch(()=>[props.comments,props.peers],markers,{deep:true})
onBeforeUnmount(()=>{editor?.dispose();model?.dispose()})
</script>
<template><div ref="host" class="monaco-host"></div></template>
