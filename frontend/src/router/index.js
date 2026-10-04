import { createRouter, createWebHistory } from 'vue-router'
import { session } from '../stores/session'
const Auth = () => import('../views/auth/Auth.vue')
const Onboarding = () => import('../views/onboarding/Onboarding.vue')
const Shell = () => import('../layouts/Shell.vue')
const Overview = () => import('../views/dashboard/Overview.vue')
const Team = () => import('../views/team/Team.vue')
const Settings = () => import('../views/settings/Settings.vue')
const Board = () => import('../views/tasks/Board.vue')
const MyTasks = () => import('../views/tasks/MyTasks.vue')
const Activity = () => import('../views/activity/Activity.vue')
const Workspace = () => import('../views/workspace/Workspace.vue')
const router = createRouter({ history: createWebHistory(), routes: [
  { path: '/login', component: Auth }, { path: '/register', component: Auth },
  { path: '/onboarding', component: Onboarding, meta: { protected: true } },
  { path: '/', component: Shell, meta: { protected: true, team: true }, children: [
    { path: '', name: 'Overview', component: Overview }, { path: 'team', name: 'Team', component: Team }, { path: 'settings', name: 'Settings', component: Settings }, { path: 'board', name: 'Task board', component: Board }, { path: 'my-tasks', name: 'My tasks', component: MyTasks }, { path: 'activity', name: 'Activity', component: Activity }, { path:'workspace',name:'Workspace',component:Workspace }
  ] }, { path: '/:pathMatch(.*)*', redirect: '/' }
] })
router.beforeEach(async to => {
  await session.init()
  if (session.state.error) return true
  if (to.meta.protected && !session.state.user) return '/login'
  if (to.meta.team && !session.state.teams.length) return '/onboarding'
  if (['/login', '/register'].includes(to.path) && session.state.user) return session.state.teams.length ? '/' : '/onboarding'
})
window.addEventListener('session-expired', () => { session.clear(); router.replace('/login') })
export default router
