<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SelectButton from 'primevue/selectbutton'
import UploadZone from './components/UploadZone.vue'
import ImageComparer from './components/ImageComparer.vue'
import TaskProgress from './components/TaskProgress.vue'
import UserButton from './components/UserButton.vue'
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
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <header class="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
      <div class="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div class="flex items-center gap-3">
          <img
            src="/logo_agenteresolve.png"
            alt="Agenteresolve"
            class="h-8 w-auto"
          >
          <span class="text-lg font-semibold text-foreground">ImageUp</span>
        </div>

        <nav class="hidden items-center gap-5 text-sm text-muted-foreground md:flex">
          <a
            href="https://bg-removal.agenteresolve.com.br"
            class="transition-colors hover:text-foreground"
          >Remover fundo</a>
          <a
            href="https://qrcode.agenteresolve.com.br"
            class="transition-colors hover:text-foreground"
          >QR Code</a>
          <a
            href="https://imposition.agenteresolve.com.br"
            class="transition-colors hover:text-foreground"
          >Imposição</a>
        </nav>

        <div class="flex items-center gap-3">
          <div
            v-if="health"
            class="hidden items-center gap-2 text-xs text-muted-foreground sm:flex"
          >
            <span
              class="inline-block h-2 w-2 rounded-full"
              :class="health.ml_available ? 'bg-success' : 'bg-amber-400'"
            />
            backend: <span class="font-mono">{{ health.backend }}</span>
          </div>
          <UserButton />
        </div>
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl flex-1 space-y-6 px-4 py-8">
      <section class="mx-auto max-w-2xl text-center">
        <h1 class="text-3xl font-bold tracking-tight text-foreground">
          Enhance &amp; upscale your images with AI
        </h1>
        <p class="mt-2 text-muted-foreground">
          Real-ESRGAN upscaling in your browser. Upload a photo, our worker
          enhances it, and you get a side-by-side before/after comparison.
        </p>
      </section>

      <!-- Scale selector + output hint -->
      <section class="mx-auto flex max-w-2xl flex-col items-center gap-2">
        <div class="flex items-center gap-3">
          <span class="text-sm text-muted-foreground">Upscale:</span>
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
        class="mx-auto max-w-2xl"
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
          class="mt-3 text-center text-sm text-muted-foreground"
        >
          Output limited to {{ limits.max_input_px * 4 }}×{{ limits.max_input_px * 4 }}px.
          Need higher resolution?
          <a
            :href="CONTACT_EMAIL"
            class="text-brand hover:underline"
          >Contact us</a>
        </div>
      </section>

      <section
        v-if="resultUrl && originalUrl"
        class="mx-auto max-w-3xl space-y-3"
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
            class="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-foreground transition-colors hover:opacity-90"
          >
            ⬇ Download enhanced image
          </a>
        </div>
        <div class="text-center">
          <button
            class="inline-flex items-center rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-strong"
            @click="reset"
          >
            Enhance another image
          </button>
        </div>
      </section>

      <section
        v-else
        class="mx-auto max-w-2xl"
      >
        <UploadZone
          :limits="limits"
          :busy="busy"
          :error="error"
          @select="onSelect"
        />
      </section>

      <!-- Contact section -->
      <section class="mx-auto max-w-2xl rounded-xl border border-border bg-surface p-6 text-center">
        <h2 class="text-xl font-bold text-foreground">
          Contact
        </h2>
        <p class="mt-2 text-sm text-muted-foreground">
          For higher resolution, custom models, or commercial use:
        </p>
        <a
          :href="CONTACT_EMAIL"
          class="mt-3 inline-block font-medium text-brand hover:underline"
        >
          Contact us
        </a>
      </section>
    </main>

    <footer class="border-t border-border bg-background/80 py-6 text-sm text-muted-foreground backdrop-blur">
      <div class="mx-auto flex max-w-5xl flex-col items-center gap-2 px-4 sm:flex-row sm:justify-between">
        <span>
          Created by
          <a
            href="https://alexwebmaster.com.br"
            target="_blank"
            rel="noopener noreferrer"
            class="font-medium text-brand hover:underline"
          >alexwebmaster.com.br</a>
        </span>
        <nav class="flex flex-wrap items-center justify-center gap-4">
          <a
            href="https://agenteresolve.com.br"
            class="transition-colors hover:text-foreground"
          >Agenteresolve</a>
          <a
            href="https://bg-removal.agenteresolve.com.br"
            class="transition-colors hover:text-foreground"
          >Remover fundo</a>
          <a
            href="https://qrcode.agenteresolve.com.br"
            class="transition-colors hover:text-foreground"
          >QR Code</a>
        </nav>
      </div>
    </footer>
  </div>
</template>
