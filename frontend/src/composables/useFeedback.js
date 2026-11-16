import { ref, nextTick, onBeforeUnmount } from 'vue'

export function useFeedback() {
  const saving = ref(false)
  const saved = ref(false)
  const highlightedId = ref(null)
  const shaking = ref(false)
  let highlightTimer, shakeTimer
  function highlight(id) {
    clearTimeout(highlightTimer)
    highlightedId.value = null
    nextTick(() => {
      highlightedId.value = id
      highlightTimer = setTimeout(() => { highlightedId.value = null }, 2800)
    })
  }
  async function validate(form) {
    try { await form.validate(); return true } catch {
      saving.value = false
      shaking.value = false
      await nextTick()
      shaking.value = true
      clearTimeout(shakeTimer)
      shakeTimer = setTimeout(() => { shaking.value = false }, 500)
      const firstItem = form.$el.querySelector('.el-form-item.is-error')
      const first = firstItem?.querySelector('input:not(:disabled), textarea:not(:disabled)') || firstItem?.querySelector('[tabindex="0"]')
      first?.focus()
      first?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      return false
    }
  }
  onBeforeUnmount(() => { clearTimeout(highlightTimer); clearTimeout(shakeTimer) })
  return { saving, saved, shaking, highlightedId, highlight, validate }
}
