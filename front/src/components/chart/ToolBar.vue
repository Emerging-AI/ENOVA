<template>
  <div class="flex items-center gap-2 justify-between flex-wrap">
    <div class="flex items-center gap-2 flex-1">
      <!-- time range -->
      <div class="w-[352px] shrink-0 flex items-center">
        <TimeRangePicker :default-time="searchTimePair" @chang-time-range="handleTimeRangeChange" :clearable="false" />
      </div>
      <!-- comparison -->
      <div class="min-w-[138px] flex items-center shrink-0">
        <el-select
          v-model="comparison"
          :class="{ 'cus-select-l': comparison === 'custom' }"
          placeholder=""
          @change="changeComparison"
        >
          <el-option-group v-for="(group, index) in comparOptions" :key="index">
            <el-option
              v-for="item in group.options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-option-group>
        </el-select>
        <el-input-number
          v-show="comparison === 'custom'"
          v-model="customCompairNum"
          class="numInput"
          :min="1"
          controls-position="right"
          @change="changeCustomCompairNum"
        />
        <el-select
          v-show="comparison === 'custom'"
          v-model="customCompairUnit"
          class="!w-16 shrink-0"
          :class="{ 'cus-select-r': comparison === 'custom' }"
          placeholder=""
          @change="changeCompairUnit"
        >
          <el-option
            v-for="item in customCompairOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </div>
      <!-- auto refresh -->
      <div class="min-w-24 flex items-center shrink-0">
        <el-select
          v-model="refreshTime"
          class="autoRefreshSelect"
          :class="{ 'cus-select-l': refreshTime === 'custom' }"
          placeholder=""
          @change="changeInterval"
        >
          <template #prefix>
            <svg-icon :name="refreshTime === '0' ? 'autoRefresh' : 'auto'" size="14" />
            <span class="w-px block h-5 bg-[#E6E9EE]"></span>
          </template>
          <el-option-group v-for="(group, index) in refreshOptions" :key="index">
            <el-option
              v-for="item in group.options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-option-group>
        </el-select>
        <el-input-number
          v-show="refreshTime === 'custom'"
          v-model="customRefreshNum"
          class="numInput"
          :min=" customRefreshUnit === 'sec' ? 10 : 1"
          controls-position="right"
          @change="changCustomRefreshNum"
        />
        <el-select
          v-show="refreshTime === 'custom'"
          v-model="customRefreshUnit"
          class="!w-16 shrink-0"
          :class="{ 'cus-select-r': refreshTime === 'custom' }"
          placeholder=""
          @change="changeRefreshUnit"
        >
          <el-option
            v-for="item in customRefreshOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </div>
      <!-- refresh btn -->
      <el-tooltip
        effect="dark"
        :content="$t('common.action.refresh')"
        placement="top"
      >
      <el-button :icon="RefreshRight" class="size-8" @click="handleRefresh" />
      </el-tooltip>
    </div>
    <div class="flex items-center gap-2">
      <!-- search -->
      <el-input
        v-model="localSearchInput"
        :prefix-icon="Search"
        class="input-with-select"
        style="width: 320px"
        clearable
        :placeholder="$t('instance.inst.chartSearch')"
        @change="inputChanged"
      />
      <span>
        <span class="w-px block h-5 bg-[#E6E9EE]"></span>
      </span>
      <!-- layout -->
      <el-select
        v-model="layoutValue"
        class="layoutSelect !w-8"
        placeholder=""
        @change="changeLayout"
      >
        <template #prefix>
          <svg-icon name="setup" size="14" />
        </template>
        <el-option
          v-for="item in layoutOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Search, RefreshRight } from '@element-plus/icons-vue'
import TimeRangePicker from '../TimeRangePicker.vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useInstanceStore } from '@/stores/instance'
import { useDebounceFn } from '@vueuse/core'
import dayjs from 'dayjs'
import { useInitQueryRange } from '@/hooks/useInitQueryRange'

const { chartTimeRange, searchTimePair } = storeToRefs(useInstanceStore())

const { t } = useI18n()

let refreshTimer: number | null = null

const comparison = ref('none')
const customCompairNum = ref(1)
const customCompairUnit = ref('min')
const refreshTime = ref<string | number>(0)
const customRefreshNum = ref(1)
const customRefreshUnit = ref('min')
const localSearchInput = ref('')
const layoutValue = ref(12)

const comparOptions = [
  {
    options: [
      {
        value: 'none',
        label: t('common.title.noContrast')
      }
    ]
  },
  {
    options: [
      {
        value: '60',
        label: t('common.time.lastHour')
      },
      {
        value: '1440',
        label: t('common.time.lastDay')
      },
      {
        value: '10080',
        label: t('common.time.lastWeek')
      },
      {
        value: '43200',
        label: t('common.time.lastMonth')
      }
    ]
  },
  {
    options: [
      {
        value: 'custom',
        label: t('common.title.customContrast')
      }
    ]
  }
]

const refreshOptions = [
  {
    options: [
      {
        value: 0,
        label: t('common.title.noRefresh')
      }
    ]
  },
  {
    options: [
      {
        label: '1m',
        value: 60
      },
      {
        label: '5m',
        value: 300
      },
      {
        label: '30m',
        value: 1800
      },
      {
        label: '1h',
        value: 3600
      }
    ]
  },
  {
    options: [
      {
        value: 'custom',
        label: t('common.title.customRefresh')
      }
    ]
  }
]

const layoutOptions = [
  {
    value: 24,
    label: 1
  },
  {
    value: 12,
    label: 2
  },
  {
    value: 8,
    label: 3
  },
  {
    value: 6,
    label: 4
  }
]

const customRefreshOptions = [
  {
    value: 'sec',
    label: t('common.time.second')
  },
  {
    value: 'min',
    label: t('common.time.minute')
  },
  {
    value: 'hour',
    label: t('common.time.hour')
  }
]

const customCompairOptions = [
  {
    value: 'min',
    label: t('common.time.minute')
  },
  {
    value: 'hour',
    label: t('common.time.hour')
  },
  {
    value: 'day',
    label: t('common.time.day')
  },
  {
    value: 'week',
    label: t('common.time.week')
  }
]

const emit = defineEmits(['changeComparison', 'changeInterval', 'changeCompairUnit', 'changeRefreshUnit', 'changeLayout', 'changeSearchVal', 'refreshChart'])

const getIntervalByUnit = (num: number | string, unit: string): number => {
  const _num = Number(num);
  switch (unit) {
    case 'sec':
      return _num;
    case 'min':
      return _num * 60;
    case 'hour':
      return _num * 60 * 60;
    case 'day':
      return _num * 60 * 60 * 24;
    case 'week':
      return _num * 60 * 60 * 24 * 7;
    default:
      throw new Error('Invalid unit');
  }
}

const changCustomRefreshNum = useDebounceFn((val) => {
  const num = getIntervalByUnit(val, customRefreshUnit.value)
  changeInterval(num)
}, 1000)

const changeRefreshUnit = (val: string) => {
  if (val === 'sec') {
    customRefreshNum.value = Math.max(10, customRefreshNum.value)
  }
  const num = getIntervalByUnit(customRefreshNum.value, val)
  changeInterval(num)
}

const changeComparison = (val: string | number) => {
  emit('changeComparison', Number(val))
}

const changeCustomCompairNum = useDebounceFn((val) => {
  const num = getIntervalByUnit(val, customCompairUnit.value)
  changeComparison(num)
}, 1000)


const changeCompairUnit = (val: string) => {
  const num = getIntervalByUnit(customCompairNum.value, val)
  changeComparison(num)
}

const changeInterval = (val: string | number) => {
  clearTimer()
  if (val === 0) return
  let num = val
  if (val === 'custom') {
    num = getIntervalByUnit(customRefreshNum.value, customRefreshUnit.value)
  }
  refreshTimer = setInterval(() => {
    handleRefresh()
  }, Number(num) * 1000)
}

const clearTimer = (): void => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

const inputChanged = () => {
  emit('changeSearchVal', localSearchInput.value)
}

const changeLayout = () => {
  emit('changeLayout', layoutValue.value)
}

const handleTimeRangeChange = (val: string[]) => {
  chartTimeRange.value = [dayjs(new Date(val[0])).format('YYYY-MM-DD HH:mm:ss'), dayjs(Math.min(new Date(val[1]).getTime(), Date.now())).format('YYYY-MM-DD HH:mm:ss')]
}

const handleRefresh = () => {
  emit('refreshChart')
}

onMounted(() => {
  useInitQueryRange()
})

</script>
<style lang="scss">
.layoutSelect {
  .el-select__suffix {
    @apply hidden;
  }
  .el-select__wrapper {
    @apply px-2;
  }
  .el-select__prefix {
    @apply size-4 flex justify-center;
  }
}
.autoRefreshSelect {
  .el-select__prefix {
    @apply gap-1;
  }
  .el-select__placeholder {
    @apply min-w-[30px];
  }
}
.numInput {
  .el-input__wrapper {
    @apply pl-2.5 pr-9 rounded-none #{!important};
  }
  .el-input__inner {
    @apply min-w-5 text-left;
  }
}
.el-select {
  &.cus-select-l {
    .el-select__wrapper {
      @apply rounded-r-none #{!important};
    }
  }
  &.cus-select-r {
    .el-select__wrapper {
      @apply rounded-l-none #{!important};
    }
  }
}
</style>
