import test from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'
import { useTaskFilters } from '../src/composables/useTaskFilters.js'
import { due, today } from '../src/utils/format.js'

const item = (id, changes={}) => ({id,title:'API task',description:'Permission boundaries',assigned_to:7,assignee:{name:'Sam Rivera'},status:'TODO',priority:'HIGH',deadline:today(),progress:0,updated_at:'2026-10-01T12:00:00Z',...changes})
const dateIn = days => { const d=new Date(`${today()}T12:00:00`); d.setDate(d.getDate()+days); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }

test('search, status, priority, assignee and due filters combine; clear restores defaults',()=>{
  const model=useTaskFilters(ref([item(1,{status:'REVIEW'}),item(2,{assigned_to:null,assignee:null}),item(3,{priority:'LOW'})]))
  Object.assign(model.filters,{query:'sam',status:'REVIEW',priority:'HIGH',assignee:7,due:'Due today'})
  assert.deepEqual(model.tasks.value.map(t=>t.id),[1])
  model.filters.priority='LOW'; assert.equal(model.tasks.value.length,0)
  model.reset(); assert.equal(model.tasks.value.length,3)
  model.filters.assignee='none'; assert.deepEqual(model.tasks.value.map(t=>t.id),[2])
  model.reset(); model.filters.query='permission'; assert.equal(model.tasks.value.length,3)
})

test('calendar deadline states distinguish overdue, today, soon, upcoming and completed',()=>{
  assert.equal(due(item(1,{deadline:dateIn(-1)})),'Overdue')
  assert.equal(due(item(1)),'Due today')
  assert.equal(due(item(1,{deadline:dateIn(3)})),'Due soon')
  assert.equal(due(item(1,{deadline:dateIn(4)})),'Upcoming')
  assert.equal(due(item(1,{deadline:null})),'No deadline')
  assert.equal(due(item(1,{status:'DONE',deadline:dateIn(-1)})),'Completed')
})

test('sorts are deterministic and missing deadlines sort last',()=>{
  const model=useTaskFilters(ref([item(3,{priority:'LOW',progress:20,deadline:null}),item(2,{priority:'URGENT',progress:90}),item(1,{priority:'URGENT',progress:90,updated_at:'2026-10-02T12:00:00Z'})]))
  assert.deepEqual(model.tasks.value.map(t=>t.id),[1,2,3])
  for(const sort of ['priority','progress','deadline']) { model.filters.sort=sort; assert.deepEqual(model.tasks.value.map(t=>t.id),[1,2,3]) }
})

test('filters react to persisted reassignment and status/progress replacement',()=>{
  const source=ref([item(1),item(2)])
  const model=useTaskFilters(source); model.filters.assignee=7
  source.value=[item(1,{assigned_to:8}),item(2,{status:'DONE',progress:100})]
  assert.deepEqual(model.tasks.value.map(t=>t.id),[2])
  model.filters.due='Completed'; assert.deepEqual(model.tasks.value.map(t=>t.id),[2])
  model.filters.status='REVIEW'; assert.equal(model.tasks.value.length,0)
})
