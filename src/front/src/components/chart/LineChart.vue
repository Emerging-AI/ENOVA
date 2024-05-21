<template>
  <div
    ref="chartContainer"
    class="bg-white rounded"
    :style="{ width: '100%', height: '240px' }"
  ></div>
  <div
    v-if="chartData.length === 0"
    class="absolute top-2 left-0 w-full h-full p-2 gap-2 pointer-events-none flex flex-col justify-center items-center"
  >
    <img src="@/assets/empty.png" class="object-contain max-h-[60%]" alt="" />
    <span>{{ $t('chart.title.noData') }}</span>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as echarts from 'echarts'
import { nextTick } from 'vue'
import { getMonitorData } from '@/api/instance'
import { storeToRefs } from 'pinia'
import { useInstanceStore } from '@/stores/instance'
import { watch } from 'vue'
const { chartQuery, activeEnodeJob } = storeToRefs(useInstanceStore())

const props = defineProps({
  chartTitle: {
    type: String,
    default: ''
  },
  queryParams: {
    type: String,
    default: ''
  },
  queryStep: {
    type: String,
    require: false,
    default: '60s'
  },
  unit: {
    type: String,
    default: '%'
  },
  searchVal: {
    type: String,
    default: ''
  },
  compareTime: {
    type: Number,
    default: 0,
    required: false
  },
  seriesName: {
    type: String,
    default: '',
    required: false
  },
  groupName: {
    type: String,
    defeult: '',
    required: false
  }
})

const emit = defineEmits(['update:unit'])

const chartInstance = ref()
const chartData = ref<any>([])

const config = computed(() => {
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      confine: true,
      enterable: false
    },
    legend: {
      show: true,
      type: 'scroll',
      bottom: 0,
      left: 8,
      itemWidth: 16,
      itemHeight: 6
    },
    grid: {
      left: '16px',
      right: '16px',
      top: '50px',
      bottom: '20px',
      containLabel: true
    },
    xAxis: [
      {
        type: 'time',
        show: chartData.value.length > 0,
        axisLabel: {
          interval: 50,
          hideOverlap: true
        }
      },
      {
        type: 'time',
        show: props.compareTime > 0 && chartData.value.length > 0,
        axisLabel: {
          interval: 50,
          hideOverlap: true
        }
      }
    ],
    yAxis: {
      type: 'value'
    },
    series: chartData.value
  }
})

const formattedSize = (data: number[]): { size: number; unit: string } => {
  const sum = data.reduce((acc, val) => {
    if (Array.isArray(val)) {
      return (isNaN(acc) ? 0 : acc) + val.reduce((a, v) => a + (isNaN(v) ? 0 : v), 0)
    }
    return (isNaN(acc) ? 0 : acc) + (isNaN(val) ? 0 : val)
  }, 0)
  const avg = sum / (data.length || 1)
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s']
  const unitIndex = Math.min(units.length - 1, Math.floor(Math.log10(avg) / 3))
  return { size: Math.pow(1024, unitIndex), unit: units[unitIndex] }
}

const formData = (data: number, size?: number): string => {
  if (props.unit === 's') {
    return Number(data / 1000).toFixed(3)
  } else if (props.unit === 'GB') {
    return Number(data / 1024 / 1024 / 1024).toFixed(3)
  } else if (props.unit === 'MB/s') {
    return size === 0
      ? Number(data / 1024 / 1024).toFixed(3)
      : Number(data / (size ?? 1)).toFixed(3)
  } else if (props.unit === 'MHz') {
    return Number(data / 1000000).toFixed(3)
  } else {
    return Number(data).toFixed(3)
  }
}

const getChartData = async (offsetTime?: number) => {
  if (props.queryParams === '') return []
  const { start, end } = chartQuery.value
  let _start = start
  let _end = end
  if (offsetTime) {
    _start = ((Number(start) - offsetTime) * 1000) / 1000
    _end = ((Number(end) - offsetTime) * 1000) / 1000
  }
  const params = `query=${props.queryParams}&start=${_start}&end=${_end}&step=${props.queryStep}`
  const res = await getMonitorData(params)
  return res.data.result
}
const chartContainer = ref(null)

const initChart = async (): Promise<void> => {
  if (chartInstance.value != null) {
    chartInstance.value.dispose()
  }
  const chart = echarts.init(chartContainer.value)
  chartInstance.value = chart
  chart.showLoading()
  let data = []
  let data2 = []
  try {
    data = await getChartData()
    if (props.compareTime > 0) {
      data2 = await getChartData(props.compareTime)
    }
  } catch (error) {
    data = []
    data2 = []
  }
  let size = 0
  if (props.unit === 'MB/s') {
    const { size: _size, unit } = formattedSize(
      data.map((i: any) => i.values.map((j: any) => Number(j[1])))
    )
    size = _size
    if (unit != null) {
      emit('update:unit', unit)
    }
  }
  if (data != null && data.length > 0) {
    const _data1 = props.seriesName === 'exported_job' ? data.filter((i: any) => i.metric.exported_job.includes(activeEnodeJob.value)) : data;
    const _data2 = props.seriesName === 'exported_job' ? data2.filter((i: any) => i.metric.exported_job.includes(activeEnodeJob.value)) : data2;
    const series1 = _data1.map((i: any) => {
      return {
        name: i.metric[props.seriesName] ?? 'value',
        type: 'line',
        smooth: true,
        emphasis: {
          focus: 'series'
        },
        symbol: 'circle',
        symbolSize: 4,
        data: i.values.map((i: Array<number>) => {
          return [Number(i[0]) * 1000, formData(i[1], size)]
        })
      }
    })
    const series2 = _data2.map((i: any) => {
      return {
        name: i.metric[props.seriesName] ?? 'value',
        type: 'line',
        xAxisIndex: 1,
        data: i.values.map((i: Array<number>) => {
          return [Number(i[0]) * 1000, formData(i[1])]
        })
      }
    })
    chartData.value = [...series1, ...series2]
  } else {
    chartData.value = []
    chart.clear()
  }
  chart.setOption(config.value)
  chart.hideLoading()
}

const resizeChart = () => {
  nextTick(() => {
    ;(chartInstance.value as any)?.resize({
      animation: {
        duration: 200,
        easing: 'linear'
      }
    })
  })
}

defineExpose({
  resizeChart,
  initChart,
  groupName: props.groupName
})

onMounted(() => {
  initChart()
})

watch(
  () => chartQuery.value,
  (val, oVal) => {
    if (oVal.start !== '' && JSON.stringify(val) !== JSON.stringify(oVal)) {
      initChart()
    }
  }
)
watch(
  () => props.compareTime,
  async () => {
    initChart()
  }
)
</script>
