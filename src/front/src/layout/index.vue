<template>
  <div class="w-screen h-screen overflow-hidden">
    <el-container class="h-full">
      <el-header class="!p-0">
        <Header />
      </el-header>
      <el-container class="h-full">
        <el-aside
          class="transition-width duration-300"
          :class="{ '!w-16': isCollapse, '!w-[210px]': !isCollapse }"
          width="210px"
        >
          <Sidebar @toggle-collapse="toggleCollapse" />
        </el-aside>
        <el-main class="!p-0 !m-0 !overflow-hidden">
          <TransitionGroup name="fade-transform">
            <router-view :key="key" />
          </TransitionGroup>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import Header from './header/index.vue'
import Sidebar from './sidebar/index.vue'

const isCollapse = ref(false)
const route = useRoute()
const key = computed(() => route.path)

const toggleCollapse = (val: boolean): void => {
  isCollapse.value = val
}
</script>
<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
/* fade-transform */
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all .5s;
}

.fade-transform-enter {
  opacity: 0;
  transform: translateX(-30px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>