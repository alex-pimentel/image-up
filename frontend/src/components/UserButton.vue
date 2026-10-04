<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { clerkEnabled, getClerk, initClerk } from '../services/clerk'

const target = ref<HTMLDivElement | null>(null)
const ready = ref(false)

onMounted(async () => {
  const clerk = await initClerk()
  if (!clerk || !target.value) return
  try {
    clerk.mountUserButton(target.value)
    ready.value = true
  } catch (e) {
    console.warn('[clerk] failed to mount user button; continuing anonymously', e)
  }
})

onBeforeUnmount(() => {
  const clerk = getClerk()
  if (clerk && target.value) clerk.unmountUserButton(target.value)
})
</script>

<template>
  <div v-show="clerkEnabled" ref="target" class="flex min-h-8 items-center" />
  <a
    v-if="!clerkEnabled || !ready"
    href="https://agenteresolve.com.br"
    class="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
  >
    Entrar
  </a>
</template>
