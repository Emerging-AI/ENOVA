<template>
  <el-row class="h-full bg-[#242424]">
    <el-col :span="8" :sm="8" :md="5">
      <img
        v-if="navLogo.src"
        class="ml-6"
        :style="{ height: navLogo.height, width: navLogo.width }"
        :src="navLogo.src"
        :alt="navLogo.alt"
      />
    </el-col>
    <el-col :span="12" :sm="12" :md="16"> </el-col>
    <el-col :span="4" :sm="4" :md="3">
      <div class="flex items-center w-full h-full justify-end pr-6">
        <Language />
      </div>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { storeToRefs } from 'pinia'
import Language from '@/components/Language.vue'
const appStore = useAppStore()
const { navLogo } = storeToRefs(appStore)
</script>

