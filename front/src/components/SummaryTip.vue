<template>
  <div
    class="text-base text-primary font-semibold leading-6 px-5 py-3 -mx-5 border-b border-gray2"
  >
    <span>{{ title }}</span>
    <span class="ml-1 text-gray5">({{ count }})</span>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'

defineProps<{
  title: string
  count: number
}>()
</script>
