<template>
  <main class="flex h-full flex-col pb-5 px-4">
    <SummaryTip :title="$t('instance.title.llmInstance')" :count="instanceList.length" />
    <div class="flex flex-col w-full h-full flex-1">
      <div class="flex justify-between flex-row-reverse items-center py-4">
        <SearchInput
          :search-tips="$t('instance.inst.searchPlaceholder')"
          @change-search="handleSearch"
        />
      </div>
      <el-table
        class="enova-table flex-1"
        :data="tableData"
        style="width: 100%"
        v-loading="tableLoading"
      >
        <template v-for="column in columns" :key="column.prop">
          <el-table-column
            v-if="columnsVisible.includes(column.prop)"
            :prop="column.prop"
            :label="column.label"
            :fixed="column.fixed"
            :column-key="column.prop"
            :sortable="column.sortable"
            :sort-orders="['ascending', 'descending']"
            :filters="column.filterData"
            :width="column.width"
            :min-width="column.minWidth"
          >
            <template #header v-if="column.prop === 'operation'">
              <div class="flex items-center justify-between relative h-full">
                <span class="text-regular">{{ column.label }}</span>
                <span class="!absolute h-12 w-px bg-[#CDD0D6] right-8" />
                <el-popover placement="bottom-end" :width="columnsPopoverWidth" trigger="click">
                  <template #reference>
                    <span class="inline-block">
                      <Setting class="size-4 cursor-pointer outline-none" />
                    </span>
                  </template>
                  <el-checkbox-group class="flex flex-col" v-model="columnsVisible">
                    <el-checkbox
                      v-for="item in columns"
                      :key="item.prop"
                      :label="item.label"
                      :value="item.prop"
                      :disabled="['instance_name', 'operation'].includes(item.prop)"
                      class="!m-0"
                    />
                  </el-checkbox-group>
                </el-popover>
              </div>
            </template>
            <template #default="scope">
              <template v-if="column.prop === 'instance_name'">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="showDetail(scope.row, 'detail')"
                  >{{ scope.row.instance_name }}</el-button
                >
              </template>
              <template v-if="column.prop === 'deploy_status'">
                <div class="flex items-center gap-3">
                  <span
                    class="shrink-0 w-3 h-3 block border-2 rounded-full"
                    :style="{ borderColor: statusMap[scope.row.deploy_status]?.color }"
                  />
                  <span>{{ statusMap[scope.row.deploy_status]?.text }}</span>
                </div>
              </template>
              <template v-if="column.prop === 'creator'">
                <div class="flex items-center gap-2">
                  <svg-icon name="user" class="shrink-0 text-[#c0c4cc]" />
                  <span>{{ scope.row.creator }}</span>
                </div>
              </template>
              <template v-if="column.prop === 'create_time'">
                <span>{{ useDateFormat(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss').value }}</span>
              </template>
              <template v-if="column.prop === 'operation'">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="showDetail(scope.row, 'config')"
                  :disabled="
                    !['running', 'scheduling', 'unknown'].includes(scope.row.deploy_status)
                  "
                  >{{ $t('instance.action.inject') }}</el-button
                >
                <el-button link type="primary" size="small" v-if="false">{{
                  $t('common.action.operationLog')
                }}</el-button>
                <el-button
                  link
                  type="primary"
                  size="small"
                  :disabled="scope.row.deploy_status !== 'running'"
                  @click="jumpToWebUI"
                >
                  WebUI
                </el-button>
                <el-popconfirm
                  :title="$t('common.inst.deleteTips')"
                  :width="180"
                  placement="bottom-end"
                  hide-icon
                  @confirm="deleteInstance(scope.row.instance_id)"
                >
                  <template #reference>
                    <el-button link type="primary" size="small">{{
                      $t('common.action.delete')
                    }}</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </template>
          </el-table-column>
        </template>
      </el-table>
      <Pagination :pagination="{ current_page: 1, page_count: 1, total: tableData.length }" />
    </div>
    <Drawer
      :showDrawer="showDrawer"
      :title="drawMainTitle"
      :title-desc="drawerTitle"
      :size="drawerType === 'detail' ? '95%' : '50%'"
      @open="openDrawer"
      @close-drawer="closeDrawer"
    >
      <InstanceDetail v-if="drawerType === 'detail'" />
      <TestConfig v-else @close-config="showDrawer = false" />
    </Drawer>
  </main>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { Setting } from '@element-plus/icons-vue'
import SummaryTip from '@/components/SummaryTip.vue'
import SearchInput from '@/components/SearchInput.vue'
import Pagination from '@/components/Pagination.vue'
import Drawer from '@/components/Drawer.vue'
import InstanceDetail from '@/components/instance/InstanceDetail.vue'
import TestConfig from '@/components/instance/TestConfig.vue'
import { useInstanceStore } from '@/stores/instance'
import { deleteServing, getDetectHistory } from '@/api/instance'
import { useDateFormat } from '@vueuse/core'
import { useInitQueryRange } from '@/hooks/useInitQueryRange'
import { useIntervalFn } from '@vueuse/core'

const { t } = useI18n()

const instanceStore = useInstanceStore()
const { currentId, instanceList, tableLoading } = storeToRefs(instanceStore)

const showDrawer = ref(false)
const drawerTitle = ref('')
const drawerType = ref('detail')
const columnsVisible = ref<string[]>([])
const searchVal = ref('')

const columnsPopoverWidth = null as unknown as undefined
const drawMainTitle = computed(() => {
  return drawerType.value === 'detail'
    ? t('instance.title.instanceDetail')
    : t('instance.title.testConfig')
})

const tableData = computed(() => {
  if (searchVal.value === '') return instanceList.value
  const search = searchVal.value.toLocaleLowerCase()
  return instanceList.value.filter(
    (item) =>
      item.instance_name.toLowerCase().includes(search) ||
      statusMap[item.deploy_status]?.text.toLowerCase().includes(search)
  )
})

const statusFilter = computed(() => {
  if (tableData.value.length === 0) return []
  return [...new Set(tableData.value.map((item) => item.deploy_status))].map((item) => ({
    text: statusMap[item] ? statusMap[item].text : item,
    value: item
  }))
})

const columns = ref([
  {
    prop: 'instance_name',
    label: t('instance.title.instanceName'),
    sortable: true,
    fixed: 'left',
    minWidth: '200px'
  },
  {
    prop: 'deploy_status',
    label: t('instance.title.deployStatus'),
    filterData: statusFilter,
    minWidth: '220px'
  },
  {
    prop: 'create_time',
    label: t('common.title.createTime'),
    sortable: true,
    minWidth: '200px'
  },
  {
    prop: 'operation',
    label: t('common.title.operation'),
    fixed: 'right',
    width: '300px'
  }
])

const statusMap: { [x: number | string]: { color: string; text: string } } = {
  pending: {
    color: '#909399',
    text: t('instance.title.deploying')
  },
  running: {
    color: '#67C23A',
    text: t('instance.title.deploySuccess')
  },
  failed: {
    color: '#F56C6C',
    text: t('instance.title.deployFail')
  },
  finsihed: {
    color: '#67C23A',
    text: t('instance.title.deploySuccess')
  },
  unknown: {
    color: '#909399',
    text: t('instance.title.deploying')
  },
  scheduling: {
    color: '#909399',
    text: t('instance.title.deploying')
  },
  error: {
    color: '#F56C6C',
    text: t('instance.title.deployFail')
  }
}

const showDetail = (row: any, type: string) => {
  currentId.value = row.instance_id
  drawerTitle.value = row.instance_name
  drawerType.value = type
  showDrawer.value = true
}

const deleteInstance = (id: string) => {
  deleteServing(id).then(() => {
    instanceStore.getInstanceList()
  })
}

const handleSearch = (val: string) => {
  searchVal.value = val
}

const jumpToWebUI = () => {
  const { protocol, hostname } = window.location
  window.open(`${protocol}//${hostname}:8501`, '_blank')
}

const { pause, resume } = useIntervalFn(() => {
  instanceStore.getInstanceList()
}, 15000)

const openDrawer = () => {
  useInitQueryRange()
  pause()
}

const closeDrawer = () => {
  showDrawer.value = false
  resume()
}
onMounted(() => {
  columnsVisible.value = columns.value.map((item) => item.prop)
  instanceStore.getInstanceList()
})
</script>
