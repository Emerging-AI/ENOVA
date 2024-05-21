<template>
  <svg aria-hidden="true" class="svg-icon" :fill="props.color" :width="width" :height="height">
    <use :xlink:href="symbolId" :fill="props.color" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps({
  name: {
    type: String,
    required: true
  },
  size: {
    type: String,
    default: '16'
  },
  width: {
    type: String
  },
  height: {
    type: String
  },
  color: {
    type: String,
    default: 'currentColor'
  }
})
const symbolId = computed(() => `#icon-${props.name}`)
const width = computed(() => (props.width ? props.width : `${props.size}px`))
const height = computed(() => (props.height ? props.height : `${props.size}px`))
</script>