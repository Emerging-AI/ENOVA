<template>
  <el-collapse class="experiment pb-7" v-model="activeNames">
    <el-collapse-item name="result">
      <template #title>
        <span class="collapse-title">{{ $t('experiment.title.testResultOverview') }}</span>
      </template>
      <el-collapse class="subCollapse px-5" v-model="activeResults">
        <el-collapse-item name="api">
          <template #title>
            <span class="collapse-title">API</span>
          </template>
          <el-row :gutter="24" class="pb-5">
            <el-col :span="6" v-for="item in apiData" :key="item.key">
              <div class="h-full flex flex-col border border-gray7 py-3 px-4 bg-white rounded">
                <span class="text-gray4 text-xs font-normal">{{ item.title }}</span>
                <span class="mt-1 text-black1">
                  <span class="font-extrabold text-2xl">{{ item.value }}</span>
                  <span class="text-xs pl-1">{{ item.unit }}</span>
                </span>
              </div>
            </el-col>
            <el-col :span="6"></el-col>
          </el-row>
        </el-collapse-item>
        <el-collapse-item name="llm">
          <template #title>
            <span class="collapse-title">LLM</span>
          </template>
          <el-row :gutter="24" class="pb-5">
            <el-col :span="6" v-for="item in llmData" :key="item.key">
              <div class="h-full flex flex-col border border-gray7 py-3 px-4 bg-white rounded">
                <span class="text-gray4 text-xs font-normal">{{ item.title }}</span>
                <span class="mt-1 text-black1">
                  <span class="font-extrabold text-2xl">{{ item.value }}</span>
                  <span class="text-xs pl-1">tokens/s</span>
                </span>
              </div>
            </el-col>
            <el-col :span="6"></el-col>
          </el-row>
        </el-collapse-item>
      </el-collapse>
    </el-collapse-item>
    <el-collapse-item name="config">
      <template #title>
        <span class="collapse-title">{{ $t('experiment.title.testConfig') }}</span>
      </template>
      <el-collapse class="subCollapse p-5 hasBorder" v-model="activeConfigs">
        <el-collapse-item name="data" class="pb-5">
          <template #title>
            <span class="collapse-title">{{ $t('common.title.data') }}</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item
              v-for="item in dataConfigs"
              :key="item.key"
              :label="item.key"
              width="25%"
            >
              {{ item.value }}
            </el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
        <el-collapse-item name="parameter">
          <template #title>
            <span class="collapse-title">{{ $t('common.title.parameters') }}</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item
              v-for="item in parameterConfigs"
              :key="item.key"
              :label="item.key"
              width="25%"
            >
              {{ item.value }}
            </el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
      </el-collapse>
    </el-collapse-item>
  </el-collapse>
</template>
<script setup lang="ts">
import { useExperimentStore } from '@/stores/experiment'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const { activeExperiment } = storeToRefs(useExperimentStore())

const activeNames = ref(['result', 'config'])
const activeResults = ref(['api', 'llm'])
const activeConfigs = ref(['data', 'parameter'])

const apiData = computed(() => {
  const { result, test_status } = activeExperiment.value ?? {
    result: { success: 0, total: 0, elasped_avg: 0 },
    test_status: 'running'
  }
  let successRate: string | number =
    result.total == null || result.total === 0
      ? 0
      : ((result.success ?? 0) / (result.total ?? 0)) * 100
  successRate = [0, 100].includes(Number(successRate))
    ? Number(successRate)
    : successRate.toFixed(3)
  const avgTime =
    Number(result.elasped_avg ?? 0) === 0 ? 0 : (Number(result.elasped_avg ?? 0) / 1000).toFixed(3)
  const isSuccess = test_status === 'success'
  return [
    {
      key: 'requestNum',
      title: t('experiment.title.requestNum'),
      value: isSuccess ? result.total ?? 0 : '-'
    },
    {
      key: 'successNum',
      title: t('experiment.title.requestSuccessNum'),
      value: isSuccess ? result.success ?? 0 : '-'
    },
    {
      key: 'successRate',
      title: t('experiment.title.requestSuccessRate'),
      value: isSuccess ? successRate : '-',
      unit: '%'
    },
    {
      key: 'avgTime',
      title: t('experiment.title.avgTime'),
      value: isSuccess ? avgTime : '-',
      unit: 's'
    }
  ]
})

const llmData = computed(() => {
  const { prompt_tps, generation_tps, test_status } = activeExperiment.value ?? {
    prompt_tps: '-',
    generation_tps: '-',
    test_status: 'running'
  }
  const isSuccess = test_status === 'success'
  return [
    {
      key: 'prompt',
      title: t('experiment.title.prompt'),
      value: isSuccess ? prompt_tps ?? 0 : '-'
    },
    {
      key: 'generation',
      title: t('experiment.title.generation'),
      value: isSuccess ? generation_tps ?? 0 : '-'
    }
  ]
})

const durationUnitMap = computed<{ [key: string]: string }>(() => {
  return {
    sec: t('common.time.second'),
    min: t('common.time.minute'),
    hour: t('common.time.hour')
  }
})

const dataConfigs = computed(() => {
  const { data_set, duration, duration_unit, distribution, tps_mean, tps_std } = activeExperiment
    .value?.test_spec || {
    test_spec: {
      data_set: '-',
      duration: '-',
      duration_unit: 'min',
      distribution: '-',
      tps_mean: '-',
      tps_std: '-'
    }
  }
  return [
    {
      key: t('common.title.dataset'),
      value: data_set || '-'
    },
    {
      key: t('instance.title.injectTime'),
      value: `${duration || '-'} ${durationUnitMap.value[duration_unit as string]}`
    },
    {
      key: t('instance.title.distribution'),
      value: distribution || '-'
    },
    {
      key: `Requests per Sec (${distribution === 'poisson' ? 'Lambda' : 'Mean'})`,
      value: tps_mean || '-'
    },
    {
      key: 'Requests per Sec (Std)',
      value: tps_std || '-'
    }
  ]
})

const parameterConfigs = computed(() => {
  const { max_tokens, temperature, top_p, others } = activeExperiment.value?.param_spec || {
    param_spec: { max_tokens: '-', temperature: '-', top_p: '-', others: '-' }
  }
  return [
    {
      key: 'Max_tokens',
      value: max_tokens || '-'
    },
    {
      key: 'Temperature',
      value: temperature || '-'
    },
    {
      key: 'Top_p',
      value: top_p || '-'
    },
    {
      key: t('instance.title.otherParams'),
      value: others || '-'
    }
  ]
})
</script>
<style lang="scss">
.experiment {
  .subCollapse {
    .el-collapse {
      &-item {
        @apply m-0;
        &__header {
          @apply bg-transparent #{!important};
        }
      }
    }
    &.hasBorder {
      .el-collapse {
        &-item {
          &__header {
            @apply bg-white border border-solid border-gray2 #{!important};
            &.is-active {
              @apply border-b-0 #{!important};
            }
          }
        }
      }
    }
  }
}
</style>
