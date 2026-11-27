<script setup>
defineProps({name:String})
const paths={shelf:'M4 4h4v16H4z M11 4h3v16h-3z M16 5l3-1 4 15-3 1z',fanqie:'M12 7c-6-4-11 3-8 9 3 6 13 6 16 0 3-6-2-13-8-9z M12 8c0-4 2-5 4-6 M8 4l4 4 4-1',qimao:'M4 11V4l6 4h4l6-4v9c0 9-16 9-16 0z M8 13h1m6 0h1m-5 3 1 1 1-1',files:'M3 7V5h7l2 3h9v12H3z',guide:'M12 6C9 4 5 4 2 5v14c4-1 7-1 10 1 3-2 6-2 10-1V5c-3-1-7-1-10 1z M12 6v14',theme:'M19 15A8 8 0 0 1 9 4a8 8 0 1 0 10 11z',search:'M16 16l5 5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0z',person:'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z M4 21v-2a8 8 0 0 1 16 0v2',link:'M9 15l6-6 M8 11l-3 3a4 4 0 0 0 6 6l3-3 M16 13l3-3a4 4 0 0 0-6-6l-3 3',arrow:'M5 12h14m-6-6 6 6-6 6'}
</script>
<template><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name]"/></svg></template>
