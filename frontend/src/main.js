import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import { definePreset } from '@primeuix/themes'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import 'bootstrap/dist/css/bootstrap-grid.min.css'
import 'bootstrap/dist/css/bootstrap-utilities.min.css'
import './assets/styles/main.css'
import './assets/styles/project.css'
import './assets/styles/workspace.css'
import './assets/styles/final.css'
import App from './App.vue'
import router from './router'

const TeamFlowTheme = definePreset(Aura, { semantic: { primary: { 50:'#f0fdfa',100:'#ccfbf1',200:'#99f6e4',300:'#5eead4',400:'#2dd4bf',500:'#14b8a6',600:'#0f817b',700:'#0f766e',800:'#115e59',900:'#134e4a',950:'#042f2e' } } })

document.documentElement.classList.remove('tf-dark')
document.documentElement.classList.add('tf-light')
createApp(App).use(PrimeVue, { theme: { preset: TeamFlowTheme, options: { darkModeSelector: false } } }).use(ToastService).use(ConfirmationService).use(router).mount('#app')
