<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

const props = defineProps<{
  beforeUrl: string
  afterUrl: string
  beforeLabel?: string
  afterLabel?: string
}>()

const pos = ref(50) // percentage 0-100
const dragging = ref(false)
const container = ref<HTMLDivElement | null>(null)

function fromClientX(clientX: number) {
  const el = container.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const pct = ((clientX - rect.left) / rect.width) * 100
  pos.value = Math.max(0, Math.min(100, pct))
}

function onPointerDown(e: PointerEvent) {
  dragging.value = true
  ;(e.target as Element).setPointerCapture?.(e.pointerId)
  fromClientX(e.clientX)
}
function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return
  fromClientX(e.clientX)
}
function onPointerUp() {
  dragging.value = false
}

onBeforeUnmount(() => {
  dragging.value = false
})
</script>

<template>
  <div
    ref="container"
    class="compare relative w-full select-none overflow-hidden rounded-2xl bg-slate-900"
    style="user-select: none"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
  >
    <!-- After (full, defines the box) -->
    <img
      :src="props.afterUrl"
      :alt="props.afterLabel || 'After'"
      class="block w-full"
      draggable="false"
      @pointerdown.stop
    >
    <!-- Before (full-size, clipped via clip-path so it stays put) -->
    <img
      :src="props.beforeUrl"
      :alt="props.beforeLabel || 'Before'"
      class="absolute inset-0 w-full h-full object-cover"
      :style="{ clipPath: `inset(0 ${100 - pos}% 0 0)` }"
      draggable="false"
      @pointerdown.stop
    >
    <span class="absolute top-2 left-2 text-xs font-semibold bg-black/60 text-white px-2 py-1 rounded pointer-events-none">
      {{ props.beforeLabel || 'Before' }}
    </span>
    <span class="absolute top-2 right-2 text-xs font-semibold bg-black/60 text-white px-2 py-1 rounded pointer-events-none">
      {{ props.afterLabel || 'After' }}
    </span>

    <!-- Slider handle -->
    <div
      class="compare-handle absolute top-0 bottom-0 w-1 bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.3)]"
      :style="{ left: pos + '%' }"
      @pointerdown.stop="onPointerDown"
    >
      <div
        class="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white text-brand-700 grid place-items-center shadow-lg pointer-events-none"
      >
        ⇆
      </div>
    </div>
  </div>
</template>