import axios from 'axios'
export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api', withCredentials: true, timeout: 12000 })
api.interceptors.request.use(async config => {
  if (['post', 'patch', 'put', 'delete'].includes(config.method)) {
    const { data } = await api.get('/auth/csrf')
    config.headers['X-CSRF-Token'] = data.csrf_token
  }
  return config
})
api.interceptors.response.use(response => response, error => {
  error.friendly = error.response?.data?.error || (error.code === 'ECONNABORTED' ? 'The server took too long to respond. Please retry.' : 'Cannot reach TeamFlow. Check that the backend is running and try again.')
  if (error.response?.status === 401 && !error.config.url.includes('/auth/')) window.dispatchEvent(new Event('session-expired'))
  return Promise.reject(error)
})
