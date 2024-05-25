<template>
  <el-dropdown style="color: #898989" trigger="click" @command="changeLanguage">
    <div class="flex items-center gap-1">
      <svg-icon name="earth" />
      <span class="flex items-center gap-1">
        {{ selectedLang }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
      </span>
    </div>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in langList"
          :key="item.value"
          :command="item"
          class="languageDropdownItem"
          :class="{ 'is-active': item.value === activeLang }"
          >{{ item.name }}</el-dropdown-item
        >
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>
<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowDown } from '@element-plus/icons-vue'
const { t, locale } = useI18n()
const selectedLang = ref('zh')
const langList = [
  {
    name: t('common.lang.zh'),
    value: 'zh_CN'
  },
  {
    name: t('common.lang.en'),
    value: 'en'
  }
]
const activeLang = ref('zh_CN')
onMounted(() => {
  const lang = localStorage.getItem('lang')
  if (lang) {
    locale.value = lang
  } else {
    locale.value = 'en'
  }
  activeLang.value = locale.value
  langList.forEach((item) => {
    if (item.value === activeLang.value) {
      selectedLang.value = item.name
      return
    }
  })
})

const changeLanguage = (command: { name: string; value: string }) => {
  const lang = command.value
  selectedLang.value = command.name
  locale.value = command.value
  activeLang.value = command.value
  localStorage.setItem('lang', lang)
  window.location.reload()
}
</script>
<style lang="scss">
.languageDropdown {
  display: inline-flex;
  align-items: center;
  word-break: keep-all;
  white-space: nowrap;
}
</style>
