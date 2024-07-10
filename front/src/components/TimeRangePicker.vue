<template>
  <el-date-picker
    v-model="searchTimePair"
    class="!w-full"
    type="datetimerange"
    :prefix-icon="Calendar"
    :range-separator="$t('common.title.to')"
    :start-placeholder="$t('common.title.startTime')"
    :end-placeholder="$t('common.title.endTime')"
    :shortcuts="shortcuts"
    :disabled-date="disabledDate"
    value-format="YYYY-MM-DD HH:mm:ss"
    @change="changeTime"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Calendar } from '@element-plus/icons-vue'
import { watch } from 'vue'

const props = defineProps({
  defaultTime: {
    type: Array<string>,
    default: () => [],
    required: false
  }
})

const { t } = useI18n()
const searchTimePair = ref<any>('')

const shortcuts = [
  {
    text: t('datepicker.lastOneHour'),
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 1)
      return [start, end]
    }
  },
  {
    text: t('datepicker.lastThreeHours'),
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 3)
      return [start, end]
    }
  },
  {
    text: t('datepicker.lastTwelveHours'),
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 12)
      return [start, end]
    }
  },
  {
    text: t('datepicker.lastTwentyFourHours'),
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24)
      return [start, end]
    }
  },
  {
    text: t('datepicker.lastTwoDays'),
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 2)
      return [start, end]
    }
  },
  {
    text: t('datepicker.lastSevenDays'),
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  },
  {
    text: t('datepicker.lastMonth'),
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    }
  }
]

const disabledDate = (val: Date) => {
  return val && new Date(val).getTime() > Date.now()
}

const emit = defineEmits(['changTimeRange'])

const changeTime = () => {
  emit('changTimeRange', searchTimePair.value)
}

watch(
  () => props.defaultTime,
  (val) => {
    if (val != null && val.length > 0) {
      searchTimePair.value = val
      changeTime()
    }
  },
  {
    immediate: true
  }
)
</script>
