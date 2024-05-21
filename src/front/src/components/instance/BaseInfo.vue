<template>
  <el-collapse v-model="activeNames">
    <el-collapse-item name="parameters">
      <template #title>
        <span class="collapse-title">{{ $t('instance.title.startupOptions') }}</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item
          v-for="item in startupConfig"
          :key="item.key"
          :label="item.key"
          width="25%"
        >
          {{ item.value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-collapse-item>
    <el-collapse-item name="specifications">
      <template #title>
        <span class="collapse-title">{{ $t('instance.title.instanceSpec') }}</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item
          v-for="item in specifications"
          :key="item.key"
          :label="item.key"
          width="25%"
        >
          {{ item.value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-collapse-item>
    <el-collapse-item name="images" v-if="false">
      <template #title>
        <span class="collapse-title">{{ $t('instance.title.instanceImage') }}</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item v-for="item in images" :key="item.key" :label="item.key" width="25%">
          {{ item.value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-collapse-item>
  </el-collapse>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInstanceStore } from '@/stores/instance'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
const { t } = useI18n()

const instanceStore = useInstanceStore()
const { activeInstance } = storeToRefs(instanceStore)

const activeNames = ref(['parameters', 'specifications'])

const startupConfig = computed(() => {
  const { startup_args } = activeInstance.value ?? { startup_args: null }
  return [
    {
      key: 'Exported_job',
      value: startup_args?.exported_job ?? '-'
    },
    {
      key: 'Dtype',
      value: startup_args?.dtype ?? '-'
    },
    {
      key: 'Load_format',
      value: startup_args?.load_format ?? '-'
    },
    {
      key: 'Max_num_batched_tokens',
      value: startup_args?.max_num_batched_tokens ?? '-'
    },
    {
      key: 'Max_num_seqs',
      value: startup_args?.max_num_seqs ?? '-'
    },
    {
      key: 'Max_paddings',
      value: startup_args?.max_paddings ?? '-'
    },
    {
      key: 'Max_seq_len',
      value: startup_args?.max_seq_len ?? '-'
    },
    {
      key: 'Model',
      value: startup_args?.model ?? '-'
    },
    {
      key: 'Tokenizer',
      value: startup_args?.tokenizer ?? '-'
    },
    {
      key: 'Pipeline_parallel_size',
      value: startup_args?.pipeline_parallel_size ?? '-'
    },
    {
      key: 'Tensor_parallel_size',
      value: startup_args?.tensor_parallel_size ?? '-'
    },
    {
      key: 'Quantization',
      value: startup_args?.quantization ?? '-'
    }
  ]
})

const specifications = computed(() => {
  const { instance_spec } = activeInstance.value ?? { instance_spec: null }
  return [
    {
      key: 'GPU',
      value: instance_spec?.gpu.product ?? '-'
    },
    {
      key: 'CPU',
      value: instance_spec?.cpu.brand_name ?? '-'
    },
    {
      key: t('instance.title.memory'),
      value: instance_spec?.memory ?? '-'
    }
  ]
})

const images = [
  {
    key: t('instance.title.imageSource'),
    value: 'Base Image'
  },
  {
    key: t('instance.title.image'),
    value: 'Python Version: 3.8 / PyTorch Version: 2.1.0 / CUDA Version: 12.2'
  }
]
</script>
