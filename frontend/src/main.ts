import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import 'primeicons/primeicons.css'
import './assets/main.css'
import App from './App.vue'
import { initClerk } from './services/clerk'

// The shared design system is dark by default; keep PrimeVue in sync.
document.documentElement.classList.add('app-dark')

// Kick off Clerk early (no-op when VITE_CLERK_PUBLISHABLE_KEY is absent).
void initClerk()

const app = createApp(App)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: { darkModeSelector: '.app-dark' },
  },
})
app.mount('#app')
