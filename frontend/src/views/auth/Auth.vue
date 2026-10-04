<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import { ArrowRight, Users, ShieldCheck, Layers } from 'lucide-vue-next'
import { api } from '../../services/api'
import { session } from '../../stores/session'
import { supabase } from '../../lib/supabase'

const route = useRoute(), router = useRouter(), register = computed(() => route.path === '/register')
const form = reactive({ name: '', email: '', password: '', confirm_password: '', remember: false }), busy = ref(false), error = ref('')

async function submit() {
  if (busy.value) return
  error.value = ''; busy.value = true
  try {
    const { data } = await api.post(register.value ? '/auth/register' : '/auth/login', form)
    session.apply(data)
    await router.push(data.teams.length ? '/' : '/onboarding')
  } catch (e) {
    error.value = e.friendly
  } finally {
    busy.value = false
  }
}

async function signInWithGoogle() {
  if (busy.value) return
  error.value = ''
  if (!supabase) {
    error.value = 'Supabase environment variables (VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY) are missing in frontend/.env'
    return
  }
  busy.value = true
  try {
    const { error: supaError } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    })
    if (supaError) error.value = supaError.message
  } catch (err) {
    error.value = err.message || 'Google sign-in failed.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth-layout">
    <aside class="auth-story">
      <div class="brand"><span class="brand-mark">T</span> TeamFlow<span class="brand-dot"></span></div>
      <div class="story-main">
        <span class="eyebrow">A PLACE TO BUILD TOGETHER</span>
        <h1>Great work starts<br>with a great team.</h1>
        <p>A shared home for the people behind your next big idea. Bring your team together and make room for what comes next.</p>
        <div class="story-diagram">
          <div class="diagram-line"></div>
          <div class="diagram-node"><Users :size="24" /><span>Your people</span></div>
          <div class="diagram-node featured"><Layers :size="24" /><span>One shared space</span></div>
          <div class="diagram-node"><ShieldCheck :size="24" /><span>Clear ownership</span></div>
        </div>
      </div>
      <div class="story-footer">Built for the way teams work.<span>TEAMFLOW / 01</span></div>
    </aside>
    <main class="auth-form-area">
      <div class="auth-form">
        <span class="eyebrow">{{ register ? 'GET STARTED' : 'WELCOME BACK' }}</span>
        <h2>{{ register ? 'Build something together.' : 'Back to your team.' }}</h2>
        <p class="text-secondary mb-4">{{ register ? 'Create your account. Your team is next.' : 'Sign in to your TeamFlow workspace.' }}</p>
        
        <button type="button" class="btn-google-auth mb-3" :disabled="busy" @click="signInWithGoogle">
          <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
            <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
          </svg>
          <span>Sign in with Google</span>
        </button>

        <div class="auth-divider"><span>OR</span></div>

        <form class="form-stack" @submit.prevent="submit">
          <template v-if="register">
            <label for="name">Full name</label>
            <InputText id="name" v-model="form.name" autocomplete="name" minlength="2" maxlength="80" required :disabled="busy" />
          </template>
          <label for="email">Email address</label>
          <InputText id="email" v-model="form.email" type="email" autocomplete="email" maxlength="254" required :disabled="busy" />
          <label for="password">Password</label>
          <Password inputId="password" v-model="form.password" :feedback="false" toggleMask :inputProps="{ autocomplete: register ? 'new-password' : 'current-password', required: true, minlength: register ? 8 : 1, maxlength: 128 }" :disabled="busy" />
          <template v-if="register">
            <p class="field-hint">At least 8 characters, including a letter and a number.</p>
            <label for="confirm">Confirm password</label>
            <Password inputId="confirm" v-model="form.confirm_password" :feedback="false" toggleMask :inputProps="{ autocomplete: 'new-password', required: true, maxlength: 128 }" :disabled="busy" />
          </template>
          <div v-else class="d-flex align-items-center gap-2 my-2">
            <Checkbox inputId="remember" v-model="form.remember" binary :disabled="busy" />
            <label for="remember" class="mb-0">Remember me</label>
          </div>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <Button type="submit" :loading="busy" :label="busy ? register ? 'Creating account…' : 'Signing in…' : register ? 'Create account' : 'Sign in'">
            <template #icon><ArrowRight :size="17" /></template>
          </Button>
        </form>
        <p class="auth-switch">
          {{ register ? 'Already part of a team?' : 'New to TeamFlow?' }}
          <RouterLink :to="register ? '/login' : '/register'" @click="error = ''">{{ register ? 'Sign in' : 'Create an account' }}</RouterLink>
        </p>
        <p class="auth-note"><ShieldCheck :size="14" /> Your workspace starts with secure access.</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.btn-google-auth {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.65rem 1rem;
  font-weight: 500;
  font-size: 0.95rem;
  color: #1e293b;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}
.btn-google-auth:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #94a3b8;
}
.btn-google-auth:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.auth-divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 1.25rem 0;
  color: #94a3b8;
  font-size: 0.8rem;
  font-weight: 600;
}
.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #e2e8f0;
}
.auth-divider span {
  padding: 0 0.75rem;
}
</style>
