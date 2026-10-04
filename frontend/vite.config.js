import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target=env.API_PROXY_TARGET || 'http://127.0.0.1:5000'
  return { plugins: [vue()], build: { rollupOptions: { output: { manualChunks: { 'vue-core': ['vue', 'vue-router'], 'prime-theme': ['@primeuix/themes', '@primeuix/themes/aura'] } } } }, server: { port: 5173, strictPort: true, proxy: { '/api': { target, changeOrigin: true }, '/socket.io':{target,ws:true,changeOrigin:true} } } }
})
