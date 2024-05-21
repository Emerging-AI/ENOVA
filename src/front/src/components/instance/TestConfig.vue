<template>
  <div class="w-full h-full pb-[84px] overflow-y-auto relative">
    <el-form
      label-position="top"
      ref="ruleFormRef"
      :rules="rules"
      label-width="auto"
      :model="formData"
      style="width: 100%"
    >
      <el-collapse class="config-collapse" v-model="activeNames">
        <el-collapse-item name="data">
          <template #title>
            <span class="collapse-title">{{ $t('common.title.data') }}</span>
          </template>
          <el-row :gutter="24" class="pt-5">
            <el-col :span="12">
              <el-form-item :label="$t('common.title.dataset')" prop="dataset">
                <el-select
                  v-model="formData.dataset"
                  :placeholder="$t('instance.inst.datastPlaceholder')"
                  popper-class="max-w-[800px]"
                >
                  <el-option-group
                    v-for="group in datasetOptions"
                    :key="group.label"
                    :label="group.label"
                  >
                    <el-option
                      v-for="item in group.options"
                      :key="item.value"
                      :label="item.tag"
                      :value="item.value"
                    >
                      <span
                        v-if="item.tag != null"
                        class="inline-block w-20 text-primary text-sm"
                        >{{ item.tag }}</span
                      >
                      <el-tooltip
                        effect="dark"
                        :content="item.detail"
                        placement="bottom"
                        :show-after="100"
                      >
                        <span class="truncate text-gray5 text-sm">{{ item.label }}</span>
                      </el-tooltip>
                    </el-option>
                  </el-option-group>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item
                class="injectTimeSelect"
                :label="$t('instance.title.injectTime')"
                prop="duration"
              >
                <el-select v-model="formData.duration" placeholder="Select">
                  <el-option
                    v-for="item in durationOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
                <el-select class="suffix !w-20" v-model="formData.duration_unit" placeholder="Select">
                  <el-option
                    v-for="item in timeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="24">
              <el-form-item :label="$t('instance.title.distribution')" prop="distribution">
                <el-radio-group v-model="formData.distribution">
                  <el-radio value="poisson">{{ $t('instance.title.poisson') }}</el-radio>
                  <el-radio value="gaussian">{{ $t('instance.title.traffic') }}</el-radio>
                </el-radio-group>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item :label="`Requests per Sec (${formData.distribution === 'poisson' ? 'Lambda' : 'Mean'})`" prop="mean">
                <el-input-number
                  v-model="formData.mean"
                  :min="0"
                  step-strictly
                  :controls="false"
                  placeholder="int, >0"
                />
              </el-form-item>
            </el-col>
            <el-col v-if="formData.distribution === 'gaussian'" :span="12">
              <el-form-item label="Requests per Sec (Std)" prop="std">
                <el-input-number
                  v-model="formData.std"
                  :min="0"
                  step-strictly
                  :controls="false"
                  placeholder="int, >0"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-collapse-item>
        <el-collapse-item name="parameters">
          <template #title>
            <span class="collapse-title">{{ $t('common.title.parameters') }}</span>
          </template>
          <el-row :gutter="24" class="pt-5">
            <el-col :span="12">
              <el-form-item label="max_tokens" prop="token">
                <el-input-number
                  v-model="formData.token"
                  :min="0"
                  :max="4096"
                  step-strictly
                  :controls="false"
                  placeholder="int, >0 and < 4096"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="temperature" prop="temperature">
                <el-input-number
                  v-model="formData.temperature"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  :precision="1"
                  step-strictly
                  :controls="false"
                  placeholder="double, >0 and < 1"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="top_p" prop="topP">
                <el-input-number
                  v-model="formData.topP"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  :precision="1"
                  step-strictly
                  :controls="false"
                  placeholder="double, >0 and < 1"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12" v-if="false">
              <el-form-item :label="$t('instance.title.otherParams')">
                <el-select
                  v-model="formData.other"
                  :placeholder="$t('instance.inst.paramsPlaceholder')"
                >
                  <el-option
                    v-for="item in praameterOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </el-collapse-item>
      </el-collapse>
    </el-form>
    <div
      class="flex flex-row-reverse gap-3 w-1/2 p-4 bg-white z-[4] border-t botder-gray2 fixed bottom-0 right-0"
    >
      <el-button type="primary" :loading="submitLoading" @click="handleConfirm">{{
        $t('instance.action.startTest')
      }}</el-button>
      <el-button type="" @click="handleClose">{{ $t('common.action.cancel') }}</el-button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { createTest } from '@/api/instance';
import { useInstanceStore } from '@/stores/instance';
import type { FormInstance, FormRules } from 'element-plus'
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router';
interface DatasetOptionsType {
  label: string
  options: {
    value: string
    tag?: string
    label: string
    detail?: string
  }[]
}

interface RuleForm {
  dataset: string
  duration: string
  distribution: string
  mean: number
  std: number
  token: number
  temperature: number
  topP: number
  other: string
}

const router = useRouter()

const { t } = useI18n()
const instanceStore = useInstanceStore()

const activeNames = ref(['data', 'parameters'])
const ruleFormRef = ref<FormInstance>()

const rules = reactive<FormRules<RuleForm>>({
  dataset: [{ required: true, message: '', trigger: 'change' }],
  duration: [{ required: true, message: '', trigger: 'change' }],
  distribution: [{ required: true, message: '', trigger: 'change' }],
  mean: [{ required: true, message: '', trigger: 'blur' }],
  std: [{ required: true, message: '', trigger: 'blur' }],
  token: [{ required: true, message: '', trigger: 'blur' }],
  temperature: [{ required: true, message: '', trigger: 'blur' }],
  topP: [{ required: true, message: '', trigger: 'blur' }]
})

const formData = ref({
  dataset: '',
  duration: '30',
  duration_unit: 'min',
  distribution: 'gaussian',
  mean: 1,
  std: 1,
  token: 1024,
  temperature: 0.9,
  topP: 0.9,
  other: ''
})

const timeOptions = [
  {
    value: 'min',
    label: t('common.time.minute')
  },
  {
    value: 'hour',
    label: t('common.time.hour')
  }
]

const datasetOptions: DatasetOptionsType[] = [
  {
    label: t('instance.title.sysDataset'),
    options: [
      {
        value: 'GSM8K',
        tag: 'GSM8K',
        label: 'datasets of grade school math word problems',
        detail:
          'GSM8K is a dataset of 8.5K high quality linguistically diverse grade school math word problems created by human problem writers.'
      },
      {
        value: 'MBPP',
        tag: 'MBPP',
        label: 'datasets of Python programming problems',
        detail:
          'MBPP consists of around 1,000 Python programming problems, including entry-level programmers, covering programming fundamentals, standard library functionality, and so on.'
      },
      {
        value: 'ARC',
        tag: 'ARC',
        label: 'datasets of multiple-choice questions  from science exams ',
        detail:
          'ARC is a multiple-choice question-answering dataset, containing questions from science exams from grade 3 to grade 9. '
      },
      {
        value: 'MC_Test',
        tag: 'MCTest',
        label: 'datasets of multiple-choice questions on machine comprehension',
        detail:
          'MCTest is a freely available set of stories and associated questions intended for research on the machine comprehension of text.'
      }
    ]
  },
  {
    label: t('instance.title.userDataset'),
    options: []
  }
]

const durationOptions = ['1', '3', '5', '15', '30', '60'].map((i) => ({ label: i, value: i }))

const praameterOptions = [
  {
    value: '1',
    label: 'params1'
  }
]

const emit = defineEmits(['closeConfig'])

const handleClose = () => {
  if (ruleFormRef.value != null) {
    ruleFormRef.value.resetFields()
  }
  emit('closeConfig')
}

const submitLoading = ref(false)
const handleConfirm = async (): Promise<void> => {
  if (ruleFormRef.value == null) return
  await ruleFormRef.value.validate((valid, fields) => {
    if (valid) {
      submitLoading.value = true
      const { dataset, duration, distribution, duration_unit, mean, std, token, temperature, topP} = formData.value;
      const params = {
        instance_id: instanceStore.currentId,
        test_spec: {
          data_set: dataset,
          duration,
          distribution,
          duration_unit,
          tps_mean: mean,
          tps_std: distribution === 'gaussian' ? std : mean
        },
        param_spec: {
          max_tokens: token,
          temperature,
          top_p: topP,
          others: ''
        },
        creator: 'admin'
      }
      createTest(params).then((res) => {
        ElMessage({
          message: t('experiment.inst.successTip'),
          type: 'success',
          duration: 3 * 1000
        })
        emit('closeConfig')
        router.push({name: 'testRecord'})
      }).finally(() => {
        submitLoading.value = false
      })
    }
  })
}
</script>
<style lang="scss">
.config-collapse {
  .el-collapse-item__content {
    @apply py-0 px-8;
  }
  .el-input-number {
    @apply w-full;
    .el-input__inner {
      @apply text-left;
    }
  }
  .injectTimeSelect {
    .el-form-item__content {
      @apply flex flex-nowrap;
      .el-select__wrapper {
        @apply rounded-r-none;
      }
      .el-select.suffix {
        .el-select__wrapper {
          @apply rounded-l-none rounded-r bg-gray8 text-gray5;
        }
        .el-select__selected-item {
          @apply text-xs text-center;
        }
        .el-select__suffix {
          @apply hidden;
        }
      }
    }
  }
}
</style>
