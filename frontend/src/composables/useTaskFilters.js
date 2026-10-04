import { reactive, computed } from 'vue'
import { due } from '../utils/format.js'
const defaults = () => ({ query: '', status: '', priority: '', assignee: '', due: '', sort: 'updated' })
export function useTaskFilters(source) {
  const filters = reactive(defaults())
  const tasks = computed(() => source.value.filter(t => {
    const query = filters.query.toLowerCase().trim()
    return (!query || `${t.title} ${t.description} ${t.assignee?.name || ''}`.toLowerCase().includes(query)) && (!filters.status || t.status === filters.status) && (!filters.priority || t.priority === filters.priority) && (filters.assignee === '' || (filters.assignee === 'none' ? t.assigned_to === null : t.assigned_to === filters.assignee)) && (!filters.due || due(t) === filters.due)
  }).sort((a,b) => {
    const rank={LOW:1,MEDIUM:2,HIGH:3,URGENT:4}
    const comparison = filters.sort === 'deadline' ? (a.deadline || '9999').localeCompare(b.deadline || '9999') : filters.sort === 'priority' ? rank[b.priority]-rank[a.priority] : filters.sort === 'progress' ? b.progress-a.progress : new Date(b.updated_at)-new Date(a.updated_at)
    return comparison || a.id-b.id
  }))
  return { filters, tasks, reset: () => Object.assign(filters, defaults()) }
}
