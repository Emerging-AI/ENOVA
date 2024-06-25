<template>
  <main class="flex h-full flex-col pb-5 px-4">
    <SummaryTip :title="$t('experiment.title.testRecord')" :count="pageData.total" />
    <div class="flex flex-col w-full h-full flex-1">
      <div class="flex flex-row-reverse gap-4 items-center py-4">
        <SearchInput
          :search-tips="$t('experiment.inst.searchPlaceholder')"
          @change-search="handleSearch"
        />
        <div class="w-[440px]">
          <TimeRangePicker @chang-time-range="changeTime" />
        </div>
      </div>
      <el-table
        class="enova-table test-record-table flex-1"
        :data="tableData"
        style="width: 100%"
        v-loading="tableLoading"
      >
        <el-table-column
          v-for="column in columns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="column.width"
          :min-width="column.minWidth"
          :fixed="column.fixed"
          :column-key="column.prop"
          :sortable="column.sortable"
          :sort-orders="['ascending', 'descending']"
          :filters="column.filterData"
          :filter-method="column.filterMethod"
          :show-overflow-tooltip="column.showTip"
        >
          <template #header="{ column }">
            <template v-if="['avg_time', 'generation_tps'].includes(column.property)">
              <el-tooltip :content="column.label">
                <span class="truncate">{{ column.label }}</span>
              </el-tooltip>
            </template>
          </template>
          <template #default="scope">
            <template v-if="column.prop === 'test_id'">
              <span
                class="cursor-pointer text-sm text-secondary font-medium"
                @click="showDetail(scope.row, 'result')"
                >{{ scope.row.test_id }}</span
              >
            </template>
            <template v-if="column.prop === 'create_time'">
              <span>{{ useDateFormat(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss').value }}</span>
            </template>
            <template v-if="column.prop === 'instanceName'">
              <el-button
                link
                type="primary"
                size="small"
                @click="showDetail(scope.row, 'detail')"
                >{{
                  instanceNameMap.get(scope.row.instance_id) ?? scope.row.instance_id
                }}</el-button
              >
            </template>
            <template v-if="column.prop === 'dataset'">
              <span>{{ scope.row.test_spec?.data_set }}</span>
            </template>
            <template v-if="column.prop === 'state'">
              <div class="flex items-center gap-3">
                <span
                  class="shrink-0 w-3 h-3 block border-2 rounded-full"
                  :style="{ borderColor: statusMap[scope.row.test_status]?.color }"
                />
                <span>{{ statusMap[scope.row.test_status]?.text }}</span>
              </div>
            </template>
            <template v-if="column.prop === 'creator'">
              <div class="flex items-center gap-2">
                <svg-icon name="user" class="shrink-0 text-[#c0c4cc]" />
                <span>{{ scope.row.creator }}</span>
              </div>
            </template>
            <template v-if="column.prop === 'generation_tps'">
              <span>{{
                scope.row.test_status === 'success' ? scope.row.generation_tps : '-'
              }}</span>
            </template>
            <template v-if="column.prop === 'avg_time'">
              <span>{{
                scope.row.test_status === 'success'
                  ? `${getAvgTime(scope.row?.result?.elasped_avg)}s`
                  : '-'
              }}</span>
            </template>
            <template v-if="column.prop === 'operation'">
              <el-button link type="primary" size="small" @click="showDetail(scope.row, 'result')">
                {{ $t('experiment.title.testResult') }}
              </el-button>
              <el-button link type="primary" size="small" v-if="false">{{
                $t('experiment.title.testLog')
              }}</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <Pagination :pagination.sync="pageData" @update:page-changed="getTableData" />
    </div>
    <Drawer
      :showDrawer="showDrawer"
      :title="drawMainTitle"
      :title-desc="drawerTitle"
      size="95%"
      @open="openDrawer"
      @close-drawer="closeDrawer"
    >
      <InstanceDetail v-if="drawerType === 'detail'" />
      <TestDetail v-else />
    </Drawer>
  </main>
</template>
<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import SummaryTip from '@/components/SummaryTip.vue'
import SearchInput from '@/components/SearchInput.vue'
import Pagination from '@/components/Pagination.vue'
import TestDetail from '@/components/experiment/TestDetail.vue'
import InstanceDetail from '@/components/instance/InstanceDetail.vue'
import TimeRangePicker from '@/components/TimeRangePicker.vue'
import { useExperimentStore } from '@/stores/experiment'
import { useInstanceStore } from '@/stores/instance'
import { useDateFormat, useIntervalFn } from '@vueuse/core'
import { useInitQueryRange } from '@/hooks/useInitQueryRange'

const { t } = useI18n()
const experimentStore = useExperimentStore()
const instanceStore = useInstanceStore()
const { testList: tableData, currentId, drawerVisible } = storeToRefs(experimentStore)
const { currentId: curInstanceId, instanceList, instanceNameMap } = storeToRefs(instanceStore)

const showDrawer = ref(false)
const drawerTitle = ref('')
const drawerType = ref('detail')
const searchTimePair = ref<string[]>([])
const tableLoading = ref(false)
const pageData = ref({
  current_page: 1,
  page_count: 10,
  total: 0,
  pageSize: 20
})

const drawMainTitle = computed(() => {
  return drawerType.value === 'detail'
    ? t('instance.title.instanceDetail')
    : t('experiment.title.testResult')
})
const statusMap: { [x: string]: { color: string; text: string } } = {
  running: {
    color: '#909399',
    text: t('experiment.title.testing')
  },
  success: {
    color: '#67C23A',
    text: t('experiment.title.testSuccess')
  },
  failed: {
    color: '#F56C6C',
    text: t('experiment.title.testFail')
  },
  unknown: {
    color: '#909399',
    text: t('experiment.title.testUnknown')
  },
  init: {
    color: '#909399',
    text: t('experiment.title.testInit')
  },
  finsihed: {
    color: '#909399',
    text: t('experiment.title.finished')
  }
}

const statusFilter = computed(() => {
  if (tableData.value.length === 0) return []
  return [...new Set(tableData.value.map((item) => item.test_status))].map((item) => ({
    text: statusMap[item]?.text ?? item,
    value: item
  }))
})

const filterStatus = (value: string, row: any) => {
  return row.test_status === value
}

const columns = ref([
  {
    prop: 'create_time',
    label: t('experiment.title.testTime'),
    sortable: true,
    minWidth: '180px'
  },
  {
    prop: 'test_id',
    label: t('experiment.title.testId'),
    width: '220px',
    showTip: true
  },
  {
    prop: 'instanceName',
    label: t('experiment.title.testInstance'),
    sortable: true,
    width: '180px'
  },
  {
    prop: 'dataset',
    label: t('experiment.title.testDataset'),
    sortable: true,
    width: '180px'
  },
  {
    prop: 'state',
    label: t('experiment.title.testStatus'),
    sortable: true,
    filterData: statusFilter,
    filterMethod: filterStatus,
    width: '180px'
  },
  {
    prop: 'generation_tps',
    label: t('experiment.title.generation'),
    sortable: true,
    minWidth: '180px'
  },
  {
    prop: 'avg_time',
    label: t('experiment.title.avgTime'),
    sortable: true,
    minWidth: '180px'
  },
  {
    prop: 'operation',
    label: t('common.title.operation'),
    fixed: 'right',
    width: '150px'
  }
])

const showDetail = (row: any, type: string) => {
  if (type === 'detail') {
    curInstanceId.value = row.instance_id
    drawerTitle.value = instanceNameMap.value.get(row.instance_id) ?? row.instance_id
  } else {
    currentId.value = row.test_id
    drawerTitle.value = row.test_id
  }
  drawerType.value = type
  showDrawer.value = true
}

const { pause, resume } = useIntervalFn(() => {
  getTableData()
}, 5000)

const closeDrawer = () => {
  drawerVisible.value = false
  showDrawer.value = false
  curInstanceId.value = ''
  currentId.value = ''
  resume()
}

const openDrawer = () => {
  drawerVisible.value = true
  useInitQueryRange()
  pause()
}

const changeTime = (val: string[]) => {
  searchTimePair.value = val
  getTableData()
}

const searchVal = ref('')
const handleSearch = (val: string) => {
  searchVal.value = val
  getTableData()
}

const checkStatus = () => {
  if (tableData.value.length === 0) return
  const needUpdate = tableData.value.some((i) => i.test_status !== 'success')
  if (!needUpdate) pause()
}

const getTableData = async () => {
  tableLoading.value = true
  const { current_page, pageSize } = pageData.value
  let params = `page=${current_page}&size=${pageSize}`
  if (searchTimePair.value != null && searchTimePair.value.length > 0) {
    params += `&start_time=${searchTimePair.value[0]}&end_time=${searchTimePair.value[1]}`
  }
  if (searchVal.value !== '') {
    params += `&fuzzy=${searchVal.value}`
  }
  try {
    const res = await experimentStore.getTestList(params)
    checkStatus()
    if (res != null) {
      pageData.value = {
        current_page: res.page,
        page_count: res.total_page,
        total: res.total_num,
        pageSize: res.size
      }
    }
  } catch (error) {
    console.log(error)
  }
  tableLoading.value = false
}

const getAvgTime = (time?: number) => {
  const _time = time != null ? Number(time) : 0
  return _time === 0 ? 0 : (_time / 1000).toFixed(3)
}

onMounted(() => {
  if (instanceList.value.length === 0) {
    instanceStore.getInstanceList()
  }
  getTableData()
})
</script>
<style lang="scss">
.test-record-table {
  thead .cell {
    @apply flex items-center;
    .el-table__column-filter-trigger {
      @apply ml-0;
    }
  }
}
</style>
