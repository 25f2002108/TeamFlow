<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../../lib/supabase'
import { api } from '../../services/api'
import { session } from '../../stores/session'

const router = useRouter()
const statusMessage = ref('Authenticating with Google...')
const errorMessage = ref('')

onMounted(async () => {
  try {
    if (!supabase) {
      errorMessage.value = 'Supabase client is not configured.'
      return
    }

    const { data: { session: supaSession }, error: sessionError } = await supabase.auth.getSession()
    
    if (sessionError || !supaSession?.user) {
      errorMessage.value = sessionError?.message || 'Failed to retrieve Google login session.'
      return
    }

    const supaUser = supaSession.user
    const email = supaUser.email
    const name = supaUser.user_metadata?.full_name || supaUser.user_metadata?.name || email.split('@')[0]

    statusMessage.value = 'Connecting to TeamFlow...'
    
    const { data } = await api.post('/auth/supabase-login', { email, name })
    session.apply(data)
    
    await router.push(data.teams.length ? '/' : '/onboarding')
  } catch (err) {
    errorMessage.value = err?.friendly || err?.message || 'Google sign-in failed. Please try again.'
  }
})
</script>

<template>
  <div class="callback-layout">
    <div class="callback-card">
      <div class="brand mb-3">
        <span class="brand-mark">T</span> TeamFlow
      </div>
      <div v-if="errorMessage" class="error-container">
        <p class="form-error" role="alert">{{ errorMessage }}</p>
        <RouterLink to="/login" class="btn-return">Return to Sign in</RouterLink>
      </div>
      <div v-else class="loading-container">
        <div class="spinner"></div>
        <p class="status-text">{{ statusMessage }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.callback-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-ground, #f8fafc);
  padding: 1.5rem;
}
.callback-card {
  background: #ffffff;
  border: 1px solid var(--surface-border, #e2e8f0);
  border-radius: 12px;
  padding: 2.5rem;
  width: 100%;
  max-width: 420px;
  text-align: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}
.brand {
  font-weight: 700;
  font-size: 1.25rem;
}
.brand-mark {
  background: #0d9488;
  color: #fff;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  margin-right: 0.25rem;
}
.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e2e8f0;
  border-top-color: #0d9488;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 1.5rem auto 1rem;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.status-text {
  color: #64748b;
  font-size: 0.95rem;
}
.form-error {
  background: #fef2f2;
  color: #991b1b;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}
.btn-return {
  display: inline-block;
  color: #0d9488;
  font-weight: 600;
  text-decoration: none;
}
</style>
