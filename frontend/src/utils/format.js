export const statuses = [{ label: 'To do', value: 'TODO' }, { label: 'In progress', value: 'IN_PROGRESS' }, { label: 'Review', value: 'REVIEW' }, { label: 'Done', value: 'DONE' }]
export const priorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'].map(value => ({ label: value[0]+value.slice(1).toLowerCase(), value }))
export function today() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }
export function calendar(value) { return value ? new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'No deadline' }
export function due(task) {
  if (task.status === 'DONE') return 'Completed'
  if (!task.deadline) return 'No deadline'
  const days = Math.round((new Date(`${task.deadline}T12:00:00`)-new Date(`${today()}T12:00:00`))/86400000)
  return days < 0 ? 'Overdue' : days === 0 ? 'Due today' : days <= 3 ? 'Due soon' : 'Upcoming'
}
export function initials(name) { return name?.split(' ').filter(Boolean).map(n=>n[0]).slice(0,2).join('').toUpperCase() || '—' }
export function timestamp(value) { return new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) }
export function size(bytes) { return bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes/1024).toFixed(1)} KB` : `${(bytes/1048576).toFixed(1)} MB` }
export function activityText(item) {
  const d = item.details, title = d.title || 'a task'
  const labels = Object.fromEntries(statuses.map(s => [s.value, s.label]))
  const workspaceActions = { WORKSPACE_IMPORTED:'imported workspace for', WORKSPACE_EXPORTED:'exported workspace for', DEPENDENCY_ADDED:'added a prerequisite to', DEPENDENCY_REMOVED:'removed a prerequisite from', DEVELOPMENT_CONFIGURED:'configured development for', EXECUTION_STARTED:'started execution for', EXECUTION_FINISHED:'finished execution for', TESTS_PASSED:'passed project tests for', TESTS_FAILED:'ran failing project tests for', TESTS_STOPPED:'stopped project tests for', FILE_CREATED: 'created file', FOLDER_CREATED: 'created folder', FILE_RENAMED: 'renamed', FILE_EDITED: 'saved', FILE_DELETED: 'deleted file', FOLDER_DELETED: 'deleted folder', PERMISSION_CHANGED: 'updated permissions for', CODE_COMMENT_ADDED: 'commented on', CODE_COMMENT_RESOLVED: 'resolved a code comment on', CODE_COMMENT_REOPENED: 'reopened a code comment on', TASK_FILE_LINKED: 'linked a file to', TASK_FILE_UNLINKED: 'unlinked a file from' }
  if (workspaceActions[item.action_type]) return `${workspaceActions[item.action_type]} ${d.path || title}`
  return ({ PROJECT_CREATED: `created project ${title}`, PROJECT_EDITED: `updated project ${title}`, TASK_CREATED: `created ${title}`, TASK_ASSIGNED: `assigned ${title} to ${d.to}`, TASK_REASSIGNED: `reassigned ${title} to ${d.to}`, TASK_EDITED: `updated ${title}`, TASK_STATUS_CHANGED: `moved ${title} to ${labels[d.after]}`, TASK_PROGRESS_CHANGED: `updated ${title} to ${d.after}%`, COMMENT_ADDED: `commented on ${title}`, ATTACHMENT_UPLOADED: `uploaded ${d.filename} to ${title}`, ATTACHMENT_DELETED: `deleted ${d.filename} from ${title}` })[item.action_type] || `updated ${title}`
}
