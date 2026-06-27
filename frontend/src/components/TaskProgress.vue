<script setup lang="ts">
import ProgressSpinner from 'primevue/progressspinner'
import type { Limits } from '../types'

const props = defineProps<{
  progressLabel: string
  elapsed: number | null
  backend: string | null
  limits: Limits | null
  running: boolean
}>()
</script>

<template>
  <div class="rounded-2xl bg-white border border-slate-200 p-6 shadow-sm">
    <div class="flex flex-col items-center gap-3 mb-3">
      <ProgressSpinner
        v-if="props.running"
        style="width: 36px; height: 36px"
        stroke-width="6"
      />
      <span
        v-else
        class="inline-block w-3 h-3 rounded-full"
        :class="props.progressLabel === 'Failed' ? 'bg-red-500' : 'bg-green-500'"
      />
      <p class="font-semibold text-slate-700">
        {{ props.progressLabel }}
      </p>
    </div>

    <div
      v-if="props.elapsed !== null"
      class="text-sm text-slate-500"
    >
      Elapsed: {{ props.elapsed.toFixed(2) }}s
    </div>

    <!-- Size restriction reminder shown during processing -->
    <div
      v-if="props.limits"
      class="mt-4 text-xs bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-3 py-2"
    >
      Input images are restricted to the largest side ≤
      <strong>{{ props.limits.max_input_px }}px</strong> in this preview build.
      Larger limits will be available for premium accounts.
    </div>

    <div
      v-if="props.backend"
      class="mt-3 text-xs text-slate-500"
    >
      Backend: <span class="font-mono">{{ props.backend }}</span>
    </div>
  </div>
</template>