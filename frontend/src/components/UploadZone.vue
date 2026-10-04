<script setup lang="ts">
import { ref } from 'vue'
import type { Limits } from '../types'

const props = defineProps<{
  limits: Limits | null
  busy: boolean
  error: string | null
}>()

const emit = defineEmits<{
  (e: 'select', file: File, url: string): void
}>()

const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const rejectReason = ref<string | null>(null)

const maxPx = () => props.limits?.max_input_px ?? 1000
const maxMb = () => props.limits?.max_upload_mb ?? 8
const allowed = () => props.limits?.allowed_extensions ?? []

function validate(file: File): string | null {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!allowed().includes(ext)) {
    return `Unsupported extension ".${ext}". Allowed: ${allowed().join(', ')}`
  }
  if (file.size > maxMb() * 1024 * 1024) {
    return `File too large. Max ${maxMb()} MB.`
  }
  return null
}

function handleFiles(files: FileList | null) {
  rejectReason.value = null
  if (!files || !files[0]) return
  const file = files[0]
  const err = validate(file)
  if (err) {
    rejectReason.value = err
    return
  }

  const url = URL.createObjectURL(file)
  const img = new Image()
  img.onload = () => {
    const longest = Math.max(img.width, img.height)
    if (longest > maxPx()) {
      rejectReason.value = `Image is ${img.width}×${img.height}px — too large. The largest side must be ≤ ${maxPx()}px.`
      URL.revokeObjectURL(url)
      return
    }
    emit('select', file, url)
  }
  img.onerror = () => {
    rejectReason.value = 'Could not read the selected image.'
    URL.revokeObjectURL(url)
  }
  img.src = url
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files) handleFiles(e.dataTransfer.files)
}

function onClick() {
  fileInput.value?.click()
}
</script>

<template>
  <div
    class="upload-zone cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-colors"
    :class="
      dragOver ? 'border-brand bg-brand/10' : 'border-border bg-surface hover:border-brand/60'
    "
    @dragover.prevent="dragOver = true"
    @dragleave.prevent="dragOver = false"
    @drop.prevent="onDrop"
    @click="onClick"
  >
    <input
      ref="fileInput"
      type="file"
      class="hidden"
      accept="image/*"
      :disabled="busy"
      @change="(e) => handleFiles((e.target as HTMLInputElement).files)"
    />
    <div class="text-5xl mb-3">🖼️</div>
    <p class="text-lg font-semibold text-foreground">Drag &amp; drop an image here</p>
    <p class="mt-1 text-sm text-muted-foreground">or click to choose a file</p>
    <div class="mt-4 space-y-1 text-xs text-muted-foreground">
      <p>Allowed: {{ allowed().join(', ') }}</p>
    </div>

    <div
      v-if="rejectReason"
      class="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-red-300"
    >
      {{ rejectReason }}
    </div>
    <div
      v-if="error"
      class="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-red-300"
    >
      {{ error }}
    </div>
  </div>
</template>
