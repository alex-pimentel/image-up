<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SelectButton from 'primevue/selectbutton'
import UploadZone from './components/UploadZone.vue'
import ImageComparer from './components/ImageComparer.vue'
import TaskProgress from './components/TaskProgress.vue'
import { api } from './services/api'
import type { Health, Limits, TaskResult } from './types'

const limits = ref<Limits | null>(null)
const health = ref<Health | null>(null)

const selectedFile = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const error = ref<string | null>(null)

const selectedScale = ref<number>(2)
const scaleOptions = [
  { label: '2x', value: 2 },
  { label: '4x', value: 4 },
]

const taskId = ref<string | null>(null)
const status = ref<TaskResult | null>(null)
const busy = ref(false)
let stopPolling: (() => void) | null = null

const originalUrl = ref<string | null>(null)
const resultUrl = ref<string | null>(null)

const CONTACT_EMAIL = 'mailto:alex@agenteresolve.com.br'

function onSelect(file: File, preview: string) {
  error.value = null
  selectedFile.value = file
  previewUrl.value = preview
  status.value = null
  resultUrl.value = null
  originalUrl.value = null
  submit()
}

async function submit() {
  if (!selectedFile.value) return
  busy.value = true
  try {
    const res = await api.enhance(selectedFile.value, selectedScale.value)
    taskId.value = res.task_id
    stopPolling = api.pollStatus(res.task_id, (r) => {
      status.value = r
      if (r.result_url) resultUrl.value = api.asset(r.result_url)
      if (r.original_url) originalUrl.value = api.asset(r.original_url)
      if (r.status === 'done' || r.status === 'error') {
        busy.value = false
        if (r.status === 'error' && !error.value) error.value = r.detail || 'Enhancement failed.'
      }
    })
  } catch (e) {
    busy.value = false
    error.value = (e as Error).message
  }
}

function reset() {
  if (stopPolling) stopPolling()
  selectedFile.value = null
  previewUrl.value = null
  taskId.value = null
  status.value = null
  resultUrl.value = null
  originalUrl.value = null
  error.value = null
  busy.value = false
}

onMounted(async () => {
  try {
    const [h, c] = await Promise.all([api.getHealth(), api.getConfig()])
    health.value = h
    limits.value = c
  } catch (e) {
    error.value = `Cannot reach backend API: ${(e as Error).message}`
  }
})

onBeforeUnmount(() => stopPolling?.())
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <img
            src="/logo_agenteresolve.png"
            alt="AgenteResolve"
            class="h-8 w-auto"
          >
          <span class="font-semibold text-lg text-slate-900">ImageUp</span>
        </div>
        <div
          v-if="health"
          class="text-xs text-slate-500 flex items-center gap-2"
        >
          <span
            class="inline-block w-2 h-2 rounded-full"
            :class="health.ml_available ? 'bg-green-500' : 'bg-amber-500'"
          />
          backend: <span class="font-mono">{{ health.backend }}</span>
        </div>
      </div>
    </header>

    <main class="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-6">
      <section class="text-center max-w-2xl mx-auto">
        <h1 class="text-3xl font-bold tracking-tight text-slate-900">
          Enhance &amp; upscale your images with AI
        </h1>
        <p class="mt-2 text-slate-700">
          Real-ESRGAN upscaling in your browser. Upload a photo, our worker
          enhances it, and you get a side-by-side before/after comparison.
        </p>
      </section>

      <!-- Scale selector + output hint -->
      <section class="max-w-2xl mx-auto flex flex-col items-center gap-2">
        <div class="flex items-center gap-3">
          <span class="text-sm text-slate-500">Upscale:</span>
          <SelectButton
            v-model="selectedScale"
            :options="scaleOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            :disabled="busy"
          />
        </div>
      </section>

      <section
        v-if="busy || status"
        class="max-w-2xl mx-auto"
      >
        <TaskProgress
          :progress-label="
            status?.status === 'pending' ? 'Queued — waiting for a worker…' :
            status?.status === 'processing' ? 'Enhancing image…' :
            status?.status === 'error' ? 'Failed' :
            'Done'
          "
          :running="busy"
          :elapsed="status?.elapsed_sec ?? null"
          :backend="status?.backend ?? null"
          :limits="limits"
        />
        <!-- result-notice contact prompt -->
        <div
          v-if="limits && resultUrl"
          class="mt-3 text-sm text-slate-500 text-center"
        >
          Output limited to {{ limits.max_input_px * 4 }}×{{ limits.max_input_px * 4 }}px.
          Need higher resolution?
          <a
            :href="CONTACT_EMAIL"
            class="text-blue-500 hover:text-blue-600 underline"
          >Contact us</a>
        </div>
      </section>

      <section
        v-if="resultUrl && originalUrl"
        class="max-w-3xl mx-auto space-y-3"
      >
        <ImageComparer
          :before-url="originalUrl"
          :after-url="resultUrl"
          before-label="Original"
          after-label="Enhanced"
        />
        <div class="flex justify-center">
          <a
            :href="resultUrl"
            download
            class="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg px-4 py-2 text-sm font-medium"
          >
            ⬇ Download enhanced image
          </a>
        </div>
        <div class="text-center">
          <button
            class="inline-flex items-center bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-lg px-4 py-2 text-sm font-medium"
            @click="reset"
          >
            Enhance another image
          </button>
        </div>
      </section>

      <section
        v-else
        class="max-w-2xl mx-auto"
      >
        <UploadZone
          :limits="limits"
          :busy="busy"
          :error="error"
          @select="onSelect"
        />
      </section>

      <!-- Contact section -->
      <section class="max-w-2xl mx-auto bg-white rounded-xl shadow-sm p-6 text-center">
        <h2 class="text-xl font-bold text-slate-900">
          Contact
        </h2>
        <p class="mt-2 text-slate-700 text-sm">
          For higher resolution, custom models, or commercial use:
        </p>
        <a
          :href="CONTACT_EMAIL"
          class="mt-3 inline-block text-blue-600 hover:text-blue-700 font-medium underline"
        >
          Contact us
        </a>
      </section>
    </main>

    <footer class="border-t border-slate-200 bg-white/80 py-6 text-center text-sm text-slate-500 backdrop-blur-sm">
      Created by
      <a
        href="https://alexwebmaster.com.br"
        target="_blank"
        rel="noopener noreferrer"
        class="font-medium text-blue-600 hover:text-blue-700"
      >alexwebmaster.com.br</a>
    </footer>
  </div>
</template>