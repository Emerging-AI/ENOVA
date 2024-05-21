<template>
  <el-config-provider :locale="locale === 'en' ? en : zhCn">
    <RouterView />
  </el-config-provider>
</template>
<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
import { useI18n } from 'vue-i18n'
const { locale } = useI18n()
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
</script>
