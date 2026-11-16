<template><span>{{ displayed }}</span></template>
<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
const props = defineProps({ value: { type: Number, default: 0 } })
const displayed = ref(0)
let frame
watch(() => props.value, value => {
  cancelAnimationFrame(frame)
  const from = displayed.value
  const start = performance.now()
  function tick(now) {
    const progress = Math.min(1, (now - start) / 850)
    displayed.value = Math.round(from + (value - from) * (1 - (1 - progress) ** 3))
    if (progress < 1) frame = requestAnimationFrame(tick)
  }
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) displayed.value = value
  else frame = requestAnimationFrame(tick)
}, { immediate: true })
onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>
