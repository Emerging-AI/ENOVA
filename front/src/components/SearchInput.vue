<template>
  <el-input
    v-model="searchInput"
    :prefix-icon="Search"
    style="width: 560px"
    clearable
    :placeholder="searchTips"
    class="input-with-select"
    @change="handleSearch"
  />
</template>
<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'

import { ref } from 'vue'

defineProps({
  searchTips: {
    type: String,
    default: ''
  }
})

const searchInput = ref('')

const emit = defineEmits(['changeSearch'])

const handleSearch = () => {
  emit('changeSearch', searchInput.value.trim())
}
</script>