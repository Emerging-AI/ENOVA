<template>
  <el-scrollbar height="100%" wrap-class="h-full sidebarScrollbar" view-class="h-[calc(100vh-60px)]">
    <el-menu class="sidebarMenu relative" router :default-active="activeMenu">
      <el-menu-item
        v-for="item in routeOptions"
        :key="item.path"
        :index="item.path"
        @mouseenter="handleMouseEnter"
        @mouseleave="handlemouseLeave"
      >
        <svg-icon :name="(item.meta?.icon as string)" class="shrink-0" />
        <template #title>{{ $t(`menu.${item.meta?.title}`) }}</template>
      </el-menu-item>
      <svg-icon
        name="toggle"
        class="text-white absolute left-4 bottom-4 cursor-pointer"
        :class="{ 'rotate-180': !isOpen }"
        @click="toggleCollapse"
      />
    </el-menu>
  </el-scrollbar>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
const route = useRoute()
const router = useRouter()

const routeOptions = router.options.routes[0].children

const activeMenu = ref('')
const isOpen = ref(true)
const sidebarHoversta = ref(false)

const isCollapse = computed(() => {
  if (isOpen.value) return false
  return !sidebarHoversta.value
})

const handleMouseEnter = (): void => {
  sidebarHoversta.value = true
  emit('toggleCollapse', isCollapse.value)
}

const handlemouseLeave = (): void => {
  sidebarHoversta.value = false
  emit('toggleCollapse', isCollapse.value)
}

onMounted(() => {
  activeMenu.value = route.path
})

const emit = defineEmits(['toggleCollapse'])

const toggleCollapse = () => {
  isOpen.value = !isOpen.value
  emit('toggleCollapse', isCollapse.value)
}
</script>

<style lang="scss" scoped>
.sidebarScrollbar {
  .el-menu {
    @apply h-full bg-[#2F374A] px-1.5 py-2 overflow-x-hidden;
    &-item {
      @apply text-white/80 text-sm rounded px-4 py-2.5 flex gap-4 items-center hover:bg-transparent hover:text-white overflow-hidden;
      &.is-active {
        @apply text-white bg-[#4E688E];
      }
    }
  }
}
</style>
