import { reactive } from 'vue'
import { io } from 'socket.io-client'
import { api } from '../services/api'
import { session } from './session'
import { projects } from './projects'
import { development } from './development'
import { workspace } from './workspace'

const state=reactive({connected:false,status:'Connecting',users:[],notifications:[],unread:0,error:'',notificationDrawer:false})
let socket, timer, editingTimer, refreshing=false, pending=false, owner=null
async function notifications(){try {const {data}=await api.get('/notifications');state.notifications=data.notifications;state.unread=data.unread;state.error=''}catch(e){state.error=e.friendly}}
async function context(){if(!socket?.connected || !session.state.activeId)return;socket.emit('join_context',{team_id:session.state.activeId,project_id:projects.state.activeId,node_id:workspace.state.inWorkspace?workspace.state.active?.id || null:null},reply=>{if(!reply?.ok)state.error=reply?.error || 'Collaboration access denied.'})}
function invalidate(){pending=true;clearTimeout(timer);timer=setTimeout(refresh,180)}
async function refresh(){
  if(refreshing || !pending)return
  if(projects.state.busy || workspace.state.saving){timer=setTimeout(refresh,180);return}
  refreshing=true;pending=false
  try {if(projects.state.activeId){await projects.refresh();await workspace.refresh();await development.load();window.dispatchEvent(new CustomEvent('teamflow-project-updated'))}}
  catch(e){state.error=e.friendly}
  finally{refreshing=false;if(pending)invalidate()}
}
async function start(){
  stop();owner=session.state.user?.id;if(!owner)return
  const user=owner;state.status='Connecting'
  try {
    const {data}=await api.get('/auth/csrf');if(user!==owner)return
    socket=io({autoConnect:false,withCredentials:true,auth:{csrf:data.csrf_token},transports:['websocket','polling']})
    socket.on('connect',()=>{state.connected=true;state.status='Live';state.error='';context();notifications();invalidate()})
    socket.on('disconnect',()=>{state.connected=false;state.status='Reconnecting';state.users=[]})
    socket.on('connect_error',()=>{state.connected=false;state.status='Reconnecting'})
    socket.on('presence_snapshot',data=>state.users=data.users)
    socket.on('project_changed',data=>{if(data.project_id===projects.state.activeId)invalidate()})
    socket.on('execution_update',development.update)
    socket.on('notifications_changed',notifications)
    socket.on('team_changed',async()=>{try {await session.refresh();await session.loadTeam();await projects.loadProjects();await workspace.tree();context()}catch(e){state.error=e.friendly}})
    socket.on('access_changed',async()=>{workspace.clear();try{await session.refresh();await session.loadTeam();await projects.loadProjects();context()}catch(e){state.error=e.friendly}})
    socket.connect();await notifications()
  }catch(e){state.status='Offline';state.error=e.friendly}
}
function stop(){owner=null;clearTimeout(timer);clearTimeout(editingTimer);socket?.disconnect();socket=null;state.connected=false;state.users=[];state.notifications=[];state.unread=0;state.status='Offline';pending=false}
function editing(value,cursor){clearTimeout(editingTimer);editingTimer=setTimeout(()=>socket?.emit('editing',{editing:value,cursor}),250)}
async function markRead(id){await api.patch(`/notifications/${id}/read`);await notifications()}
async function markAll(){await api.post('/notifications/read-all');await notifications()}
export const collaboration={state,start,stop,context,editing,notifications,markRead,markAll}
