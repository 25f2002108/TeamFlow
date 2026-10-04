<script setup>
import { LayoutDashboard, Users, Settings, ArrowUpRight, ListTodo, Columns3, Activity, Code2 } from 'lucide-vue-next'
defineEmits(['navigate'])
const links = [{ to: '/', name: 'Overview', icon: LayoutDashboard }, { to: '/my-tasks', name: 'My tasks', icon: ListTodo }, { to: '/board', name: 'Task board', icon: Columns3 }, {to:'/workspace',name:'Workspace',icon:Code2}, { to: '/team', name: 'Team', icon: Users }, { to: '/activity', name: 'Activity', icon: Activity }, { to: '/settings', name: 'Settings', icon: Settings }]
</script>
<template><div class="sidebar-inner"><div class="brand"><span class="brand-mark">T</span>TeamFlow<span class="brand-dot"></span></div><div class="sidebar-label">WORKSPACE</div><nav aria-label="Main navigation"><RouterLink v-for="link in links" :key="link.to" :to="link.to" :exact-active-class="'active'" @click="$emit('navigate')"><component :is="link.icon" :size="18" /><span>{{ link.name }}</span><ArrowUpRight class="nav-arrow" :size="15" /></RouterLink></nav><div class="sidebar-bottom"><div class="sidebar-label">CONNECTED WORK</div><p>Clear focus.<br>Shared momentum.</p><div class="foundation-line"></div><span>TeamFlow · Build together</span></div></div></template>

