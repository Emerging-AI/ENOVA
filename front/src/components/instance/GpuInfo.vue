<template>
  <section class="py-5 px-6 flex flex-col gap-5 h-full max-h-[calc(100vh-136px)] overflow-hidden">
    <ToolBar
      @change-layout="layoutChange"
      @change-search-val="searchChange"
      @refresh-chart="refreshChart"
      @change-comparison="comparisonChange"
    />
    <div
      class="flex gap-2 items-center py-2 px-4 bg-[#E6F4FF] text-sm"
      v-if="detectList.length > 0"
    >
      <svg-icon name="info" class="shrink-0 text-secondary" />
      <el-popover placement="bottom" :width="500" popper-class="p-3" trigger="click">
        <template #reference>
          <span class="text-secondary cursor-pointer">{{
            $t('instance.title.configSuggest')
          }}</span>
        </template>
        <div class="flex flex-col">
          <div class="py-3">
            <span class="text-black1 text-sm">{{ $t('instance.title.configSuggest') }}</span>
          </div>
          <el-table :data="gridData" class="configTable" width="500px">
            <el-table-column width="165px" property="data" />
            <el-table-column property="current" :label="$t('instance.title.currentVal')" />
            <el-table-column property="recommend" :label="$t('instance.title.suggestVal')" />
          </el-table>
        </div>
      </el-popover>
    </div>
    <section class="flex-1 overflow-hidden flex w-full" ref="containerRef">
      <section class="flex-1 w-[calc(100%-164px)]">
        <div
          class="h-60 overflow-auto"
          ref="containerRef1"
          :style="{ height: containerHeight + 'px' }"
        >
          <el-collapse v-model="computedNameTabs">
            <el-collapse-item
              v-for="item in monitors"
              :key="item.title"
              :name="item.title"
              :id="item.key"
              class="first:mt-0"
            >
              <template #title>
                <span class="collapse-title">{{ item.title }}</span>
              </template>
              <div class="px-4 bg-gray3">
                <el-row :gutter="16">
                  <template v-if="item.key === 'cuda'">
                    <el-col :span="24" class="pb-6 pt-2">
                      <el-table :data="cudaData" class="enova-table">
                        <el-table-column
                          prop="time"
                          :label="$t('common.title.time')"
                          sortable
                          :sort-orders="['ascending', 'descending']"
                        />
                        <el-table-column prop="xid" label="ID" />
                        <el-table-column prop="failure" :label="$t('common.title.failure')" />
                        <el-table-column prop="causes" :label="$t('common.title.causes')" />
                      </el-table>
                      <Pagination
                        layout="total, prev, pager, next"
                        :pagination="{ current_page: 1, page_count: 1, total: 0 }"
                      />
                    </el-col>
                  </template>
                  <template v-else>
                    <el-col
                      v-for="(c, index) in item.charts"
                      :key="index"
                      :span="layoutSpan"
                      class="mb-4 relative"
                    >
                      <el-tooltip
                        effect="dark"
                        :content="c.title"
                        placement="bottom"
                        :show-after="100"
                      >
                        <div
                          class="absolute top-4 left-6 w-[calc(100%-46px)] z-10 text-black1 flex items-center select-none text-xs"
                        >
                          <span class="font-bold truncate inline-block max-w-[80%]">
                            {{ c.title }}
                          </span>
                          <span v-if="c.unit && c.unit !== ''" class="text-gray4 pl-1"
                            >({{ updatedUnitMap.get(`${item.key}-${index}`) ?? c.unit }})</span
                          >
                        </div>
                      </el-tooltip>
                      <LineChart
                        ref="chartRef"
                        :chart-title="c.title"
                        :query-params="c.query"
                        :query-step="c.step"
                        :unit="updatedUnitMap.get(`${item.key}-${index}`) ?? c.unit"
                        :search-val="searchInput"
                        :compare-time="compareTime"
                        :series-name="c.name"
                        :group-name="item.title"
                        @update:unit="changeChartUnit(item, index, $event)"
                      />
                    </el-col>
                  </template>
                </el-row>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </section>
      <section class="enova-anchor w-[164px] h-full pl-5">
        <el-anchor
          ref="anchorRef"
          :container="containerRef1"
          direction="vertical"
          type="default"
          :marker="false"
          @click="clickAnchor"
        >
          <el-anchor-link
            v-for="item in cpuCardArray"
            :key="item.key"
            :href="'#' + item.key"
            :title="item.value"
          />
        </el-anchor>
      </section>
    </section>
  </section>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import ToolBar from '../chart/ToolBar.vue'
import LineChart from '../chart/LineChart.vue'
import { useI18n } from 'vue-i18n'
import Pagination from '@/components/Pagination.vue'
import { useDebounceFn } from '@vueuse/core'
import { useInstanceStore } from '@/stores/instance'
import { storeToRefs } from 'pinia'
import { getDetectHistory, getMonitorData } from '@/api/instance'
import { watch } from 'vue'

const { chartQuery, activeEnodeId } = storeToRefs(useInstanceStore())

const { t } = useI18n()
const containerRef1 = ref<HTMLElement | null>(null)
const containerRef = ref()
const anchorRef = ref()
const containerHeight = ref(2000)
const layoutSpan = ref(12)
const cpuCardArray = [
  { key: 'api', value: 'API' },
  { key: 'llm', value: 'LLM' },
  { key: 'gpu', value: 'GPU' },
  { key: 'memory', value: 'Memory' },
  { key: 'clock', value: 'Clock' },
  { key: 'power', value: 'Temperature & Power' },
  { key: 'profiling', value: 'Profiling' },
  { key: 'cuda', value: 'CUDA XID' }
]
const chartRef = ref(null)

const updatedUnitMap = ref(new Map())

const changeChartUnit = (item: any, idx: number, val: string) => {
  updatedUnitMap.value.set(`${item.key}-${idx}`, val)
}

const computedNameTabs = ref(cpuCardArray.map((i) => i.value))

const gridData = computed(() => {
  const data =
    detectList.value.length > 0
      ? detectList.value[0]
      : {
          configRecommendResult: {
            gpu_memory_utilization: 0,
            max_num_seqs: 0,
            replicas: 0,
            tensor_parallel_size: 0
          },
          currentConfig: {
            gpu_memory_utilization: 0,
            max_num_seqs: 0,
            replicas: 0,
            tensor_parallel_size: 0
          },
          isAnomaly: true,
          timestamp: 0
        }
  const { configRecommendResult: recommend, currentConfig: current } = data
  return [
    {
      data: 'batch size',
      current: current.max_num_seqs,
      recommend: recommend.max_num_seqs
    },
    {
      data: 'tensor_parallel_size',
      current: current.tensor_parallel_size,
      recommend: recommend.tensor_parallel_size
    },
    {
      data: 'gpu_memory_utilization',
      current: current.gpu_memory_utilization,
      recommend: recommend.gpu_memory_utilization
    },
    {
      data: 'replicas num',
      current: current.replicas,
      recommend: recommend.replicas
    }
  ]
})

const apiChart = computed(() => {
  return filterChartTitle(
    [
      {
        title: t('chart.title.requestNum'),
        query: 'sum(rate(http_server_requests_total{}[1m])) by (exported_job)',
        step: '60s',
        unit: '',
        name: 'exported_job'
      },
      {
        title: t('chart.title.requestExecuteNum'),
        query: 'sum(rate(http_server_response_size_bytes_count{}[1m])) by (exported_job)',
        step: '60s',
        unit: '',
        name: 'exported_job'
      },
      {
        title: t('chart.title.requestSuccessNum'),
        query:
          'sum(rate(http_server_response_size_bytes_count{http_status_code=~"2.."}[1m])) by (exported_job)',
        step: '60s',
        unit: '',
        name: 'exported_job'
      },
      {
        title: t('chart.title.requestSuccessRate'),
        query:
          'sum(rate(http_server_response_size_bytes_count{http_status_code=~"2.."}[1m])) by (exported_job) / sum(rate(http_server_response_size_bytes_count{}[1m])) by (exported_job) * 100',
        step: '60s',
        unit: '%',
        name: 'exported_job'
      },
      {
        title: t('chart.title.activeRequestNum'),
        query: 'sum(http_server_active_requests{}) by (exported_job)',
        unit: '',
        name: 'exported_job'
      },
      {
        title: t('chart.title.requestDuration'),
        query:
          'sum(rate(http_server_duration_milliseconds_sum{}[1m])) by (exported_job) / sum(rate(http_server_duration_milliseconds_count{}[1m])) by (exported_job)',
        unit: 's',
        name: 'exported_job'
      },
      {
        title: t('chart.title.responseSize'),
        query: 'sum(rate(http_server_response_size_bytes_sum{}[1m])) by (exported_job)',
        step: '60s',
        unit: 'MB/s',
        name: 'exported_job'
      },
      {
        title: t('chart.title.requestSize'),
        query: 'sum(rate(http_server_request_size_bytes_sum{}[1m])) by(exported_job)',
        step: '60s',
        unit: 'MB/s',
        name: 'exported_job'
      }
    ],
    'API'
  )
})

const llmChart = computed(() => {
  return filterChartTitle(
    [
      {
        title: t('chart.title.promptThroughput'),
        // query: 'sum (avg_prompt_throughput_tokens_per_second{}) by (exported_job)',
        query: 'sum (vllm:avg_prompt_throughput_toks_per_s{}) by (exported_job)',
        unit: 'tokens/s',
        name: 'exported_job'
      },
      {
        title: t('chart.title.generationThroughput'),
        // query: 'sum (avg_generation_throughput_tokens_per_second{}) by (exported_job)',
        query: 'sum (vllm:avg_generation_throughput_toks_per_s{}) by (exported_job)',
        unit: 'tokens/s',
        name: 'exported_job'
      },
      {
        title: t('chart.title.runningRequests'),
        // query: 'sum (running_requests{}) by (exported_job)',
        query: 'sum (vllm:num_requests_running{}) by (exported_job)',
        unit: '',
        name: 'exported_job'
      },
      {
        title: t('chart.title.pendingRequests'),
        // query: 'sum (pending_requests{}) by (exported_job)',
        query: 'sum (vllm:num_requests_waiting{}) by (exported_job)',
        unit: '',
        name: 'exported_job'
      },
      {
        title: t('chart.title.gpuKv'),
        // query: 'sum (gpu_kv_cache_usage_percent{}) by (exported_job)',
        query: 'sum (vllm:gpu_cache_usage_perc{}) by (exported_job)',
        unit: '%',
        name: 'exported_job'
      },
      {
        title: t('chart.title.timeToFirst'),
        query: 'sum(rate(vllm:time_to_first_token_seconds_sum{}[1m])) by (exported_job) / sum(rate(vllm:time_to_first_token_seconds_count{}[1m])) by (exported_job)',
        unit: 'ms',
        name: 'exported_job'
      },
      {
        title: t('chart.title.timePerOutput'),
        query: 'sum(rate(vllm:time_per_output_token_seconds_sum{}[1m])) by (exported_job) / sum(rate(vllm:time_per_output_token_seconds_count{}[1m])) by (exported_job)',
        unit: 'ms',
        name: 'exported_job'
      }
    ],
    'LLM'
  )
})

const gpuChart = computed(() => {
  return filterChartTitle(
    [
      {
        title: t('chart.title.gpuRate'),
        query: 'DCGM_FI_DEV_GPU_UTIL',
        unit: '%',
        name: 'device'
      }
    ],
    'GPU'
  )
})

const memChart = computed(() => {
  return filterChartTitle(
    [
      {
        title: t('chart.title.memRate'),
        query: 'DCGM_FI_DEV_MEM_COPY_UTIL',
        unit: '%',
        name: 'device'
      },
      {
        title: t('chart.title.fbNum'),
        query: 'DCGM_FI_DEV_FB_USED',
        unit: 'GB',
        name: 'device'
      }
    ],
    'Memory'
  )
})

const clockChart = computed(() => {
  return filterChartTitle(
    [
      {
        title: t('chart.title.smClock'),
        query: 'DCGM_FI_DEV_SM_CLOCK * 1000000',
        unit: 'MHz',
        name: 'device'
      },
      {
        title: t('chart.title.memClock'),
        query: 'DCGM_FI_DEV_MEM_CLOCK * 1000000',
        unit: 'MHz',
        name: 'device'
      }
    ],
    'Clock'
  )
})

const powerChart = computed(() => {
  return filterChartTitle(
    [
      {
        title: t('chart.title.memTemp'),
        query: 'avg by(device) (DCGM_FI_DEV_MEMORY_TEMP)',
        unit: '℃',
        name: 'device'
      },
      {
        title: t('chart.title.gpuTemp'),
        query: 'avg by(device) (DCGM_FI_DEV_GPU_TEMP)',
        unit: '℃',
        name: 'device'
      },
      {
        title: t('chart.title.power'),
        query: 'DCGM_FI_DEV_POWER_USAGE',
        unit: 'W',
        name: 'device'
      }
    ],
    'Temperature & Power'
  )
})

const profilingChart = computed(() => {
  return filterChartTitle(
    [
      {
        title: t('chart.title.grEnginActive'),
        query: '',
        unit: '%'
      },
      {
        title: t('chart.title.tensor'),
        query: '',
        unit: '%'
      },
      {
        title: t('chart.title.memCopyUtil'),
        query: '',
        unit: '%'
      },
      {
        title: t('chart.title.pcie'),
        query: '',
        unit: 'MB/s'
      },
      {
        title: t('chart.title.nvLink'),
        query: '',
        unit: 'MB/s'
      }
    ],
    'Profiling'
  )
})

const cudaData = ref([])

const monitors = computed(() => {
  return [
    {
      title: 'API',
      key: 'api',
      charts: apiChart.value,
      show: apiChart.value.length > 0
    },
    {
      title: 'LLM',
      key: 'llm',
      charts: llmChart.value,
      show: llmChart.value.length > 0
    },
    {
      title: 'GPU',
      key: 'gpu',
      charts: gpuChart.value,
      show: gpuChart.value.length > 0
    },
    {
      title: 'Memory',
      key: 'memory',
      charts: memChart.value,
      show: memChart.value.length > 0
    },
    {
      title: 'Clock',
      key: 'clock',
      charts: clockChart.value,
      show: clockChart.value.length > 0
    },
    {
      title: 'Temperature & Power',
      key: 'power',
      charts: powerChart.value,
      show: powerChart.value.length > 0
    },
    {
      title: 'Profiling',
      key: 'profiling',
      charts: profilingChart.value,
      show: profilingChart.value.length > 0
    },
    {
      title: 'CUDA XID',
      key: 'cuda'
    }
  ]
})

const clickAnchor = (e: MouseEvent) => {
  e.preventDefault()
}

const layoutChange = (val: string | number) => {
  layoutSpan.value = Number(val)
  ;(chartRef.value ?? []).forEach((item: any) => {
    item.resizeChart()
  })
}

const searchInput = ref('')
const searchChange = (val: string) => {
  searchInput.value = val
}

const refreshChart = () => {
  ;(chartRef.value ?? []).forEach((item: any) => {
    item.initChart()
  })
}

const compareTime = ref(0)
const comparisonChange = (val: number) => {
  compareTime.value = val * 60
}

const filterChartTitle = (list: any[], category: string) => {
  return list.filter(
    (item) =>
      category.toLowerCase().includes(searchInput.value.toLowerCase()) ||
      item.title.toLowerCase().includes(searchInput.value.toLowerCase())
  )
}

const debouncedFn = useDebounceFn(
  () => {
    nextTick(() => {
      containerHeight.value = containerRef.value.offsetHeight
      layoutChange(layoutSpan.value)
    })
  },
  300,
  { maxWait: 3000 }
)

const getTableData = async () => {
  const { start, end, step } = chartQuery.value
  const params = `query=count(DCGM_FI_DEV_XID_ERRORS > 0)&start=${start}&end=${end}&step=${step}&timeShift=30m`
  const res = await getMonitorData(params)
  cudaData.value = res.data.result
}

const detectList = ref([])
const getDetect = async () => {
  const params = `task_name=${activeEnodeId.value}`
  try {
    const res = await getDetectHistory(params)
    detectList.value = res.data
  } catch (error) {
    detectList.value = []
  }
}

onMounted(() => {
  nextTick(() => {
    containerHeight.value = containerRef.value.offsetHeight
    anchorRef.value?.scrollTo('#api')
  })
  getDetect()
  getTableData()
  window.addEventListener('resize', debouncedFn)
})

watch(
  () => computedNameTabs.value,
  (nv: string[], ov: string[]) => {
    if (nv.length > ov.length) {
      const diff = nv.filter((item) => !ov.includes(item))
      if (diff.length > 0 && chartRef.value != null) {
        const chartList = (chartRef.value as any[]).filter((item) => {
          return item.groupName === diff[0]
        })
        if (chartList.length > 0) {
          chartList.forEach((i) => i.resizeChart())
        }
      }
    }
  }
)
</script>
<style lang="scss">
.configTable {
  &.el-table {
    border-right: 1px solid #ebeef5;
    @apply text-xs border border-gray2 #{!important};

    th.el-table__cell {
      @apply bg-[#E6E8EB] text-regular text-xs;
    }
  }
}

.enova-anchor {
  .el-anchor.el-anchor--vertical {
    .el-anchor {
      &__list {
        @apply pl-0;
      }

      &__item {
        @apply text-primary text-xs leading-5 hover:bg-gray8 hover:rounded;
      }

      &__link {
        @apply py-1 px-2;

        &.is-active {
          @apply bg-gray3 rounded font-bold;
        }
      }
    }
  }
}
</style>
