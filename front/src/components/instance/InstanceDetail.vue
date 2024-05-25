<template>
  <el-tabs v-model="activeName" class="enova-tabs h-full">
    <el-tab-pane :label="$t('common.title.baseInfo')" name="baseInfo" :lazy="true">
      <BaseInfo />
    </el-tab-pane>
    <el-tab-pane :label="$t('common.title.metrics')" name="gpuInfo" class="h-full" :lazy="true">
      <GpuInfo />
    </el-tab-pane>
  </el-tabs>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import BaseInfo from './BaseInfo.vue'
import GpuInfo from './GpuInfo.vue';
defineProps({
  showDrawer: {
    type: Boolean,
    default: false
  }
})
const activeName = ref('baseInfo')
</script>
