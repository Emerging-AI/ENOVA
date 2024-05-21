<template>
  <div class="page-container pt-3">
    <el-pagination
      :current-page="pagination.current_page"
      :page-sizes="[10, 20, 30, 50, 80]"
      :page-size="pagination.pageSize ?? 20"
      :layout="layout"
      :page-count="pagination.page_count"
      :total="pagination.total"
      :hide-on-single-page="false"
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
    />
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'

interface Pagination {
  current_page: number
  page_count: number
  total: number
  pageSize?: number
}
const props = defineProps({
  pagination: {
    type: Object as PropType<Pagination>,
    required: true,
    default: () => ({
      current_page: 1,
      page_count: 1,
      total: 0
    })
  },
  pageSize: {
    type: Number,
    required: false,
    default: 20
  },
  layout: {
    type: String,
    required: false,
    default: 'total, sizes, prev, pager, next, jumper'
  }
})

const emit = defineEmits(['update:pageChanged'])

const handleSizeChange = (val: number): void => {
  if (val === props.pagination.pageSize) return
  props.pagination.pageSize = val
  emit('update:pageChanged', val)
  
}
const handleCurrentChange = (val: number): void => {
  if (val === props.pagination.current_page) return
  props.pagination.current_page = val
  emit('update:pageChanged', val)
}
</script>
