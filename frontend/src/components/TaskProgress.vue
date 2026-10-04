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
  <div class="rounded-2xl border border-border bg-surface p-6">
    <div class="mb-3 flex flex-col items-center gap-3">
      <ProgressSpinner v-if="props.running" style="width: 36px; height: 36px" stroke-width="6" />
      <span
        v-else
        class="inline-block h-3 w-3 rounded-full"
        :class="props.progressLabel === 'Failed' ? 'bg-destructive' : 'bg-success'"
      />
      <p class="font-semibold text-foreground">
        {{ props.progressLabel }}
      </p>
    </div>

    <div v-if="props.elapsed !== null" class="text-sm text-muted-foreground">
      Elapsed: {{ props.elapsed.toFixed(2) }}s
    </div>

    <!-- Size restriction reminder shown during processing -->
    <div
      v-if="props.limits"
      class="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200"
    >
      Input images are restricted to the largest side ≤
      <strong>{{ props.limits.max_input_px }}px</strong> in this preview build. Larger limits will
      be available for premium accounts.
    </div>

    <div v-if="props.backend" class="mt-3 text-xs text-muted-foreground">
      Backend: <span class="font-mono">{{ props.backend }}</span>
    </div>
  </div>
</template>
