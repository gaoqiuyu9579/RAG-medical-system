// 返回纯文本片段，通过 Vue 插值渲染，资料中的 HTML 不会执行。
export function highlightExcerpt(text, question) {
  const tokens = question.match(/[\p{L}\p{N}]+/gu) || []
  const terms = new Set()
  for (const token of tokens) {
    if (/^[\x00-\x7f]+$/.test(token)) { if (token.length > 1) terms.add(token); continue }
    for (let size = 2; size <= Math.min(8, token.length); size++) {
      for (let i = 0; i + size <= token.length; i++) terms.add(token.slice(i, i + size))
    }
  }
  const hit = Array(text.length).fill(false)
  for (const term of terms) {
    let index = text.indexOf(term)
    while (index >= 0) { hit.fill(true, index, index + term.length); index = text.indexOf(term, index + term.length) }
  }
  const parts = []
  for (let i = 0; i < text.length; i++) {
    if (!parts.length || parts.at(-1).hit !== hit[i]) parts.push({ text: '', hit: hit[i] })
    parts.at(-1).text += text[i]
  }
  return parts
}
