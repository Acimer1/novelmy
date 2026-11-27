<script setup>
import { ref, watch } from 'vue'
const props = defineProps({ book: { type: Object, required: true } })
const failed = ref(false)
watch(() => props.book.cover_url, () => { failed.value = false })
</script>
<template>
  <div class="cover" aria-hidden="true">
    <img v-if="book.cover_url && !failed" :src="book.cover_url" alt="" @error="failed = true">
    <span v-else>{{ Array.from((book.book_name || book.title || '书').trim())[0] || '书' }}</span>
  </div>
</template>
