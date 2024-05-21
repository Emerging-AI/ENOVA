<template>
  <el-drawer
    :model-value="showDrawer"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :size="size"
    class="enova-drawer"
    custom-class="enova-drawer"
    @close="handleClose"
  >
    <template #header>
      <p class="inline-flex items-center gap-1">
        <span class="text-base font-bold text-[#1D2129]">{{ title }}</span>
        <span class="text-sm text-[#86909C]">- {{ titleDesc }}</span>
      </p>
    </template>
    <slot></slot>
  </el-drawer>
</template>
<script setup lang="ts">
const props = defineProps({
  showDrawer: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  titleDesc: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: '50%'
  }
})
const emit = defineEmits(['closeDrawer'])
const handleClose = () => {
  emit('closeDrawer', false)
}
</script>
<style lang="scss">
.enova-drawer {
  .el-drawer__header {
    @apply m-0 py-3 px-4 border-b border-[#E5E6EB]
  }
  .el-drawer__body {
    @apply p-0;
  }
}
</style>
