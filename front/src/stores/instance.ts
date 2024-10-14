import { defineStore } from 'pinia'
import type { InstanceType } from './config'
import { getServing } from '@/api/instance'
interface instanceStoreState {
  instanceList: InstanceType[]
  currentId: string
  chartTimeRange: string[]
  tableLoading: boolean
  searchTimePair: string[]
}
interface chartQueryParams {
  start: string | number
  end: string | number
  step: string | number
}

export const useInstanceStore = defineStore('instance', {
  state: (): instanceStoreState => ({
    instanceList: [],
    currentId: '',
    chartTimeRange: [],
    tableLoading: false,
    searchTimePair: []
  }),
  getters: {
    activeInstance(): InstanceType | undefined {
      return this.instanceList.find((item: InstanceType) => item.instance_id === this.currentId)
    },
    instanceNameMap(): Map<string, string> {
      const res = new Map<string, string>()
      this.instanceList.forEach((item: InstanceType) => {
        res.set(item.instance_id, item.instance_name)
      })
      return res
    },
    chartQuery(): chartQueryParams {
      const [start, end] = this.chartTimeRange
      const _start = start ? Math.floor(new Date(start).getTime() / 1000).toFixed(3) : ''
      const _end = end ? Math.floor(new Date(end).getTime() / 1000).toFixed(3) : ''
      return {
        start: _start,
        end: _end,
        step: '15s'
      }
    },
    activeServingId(): string {
      return this.activeInstance != null ? this.activeInstance.serving_id : this.instanceList[0]?.serving_id ?? ''
    },
    activeServingJob(): string {
      return this.activeInstance != null ? this.activeInstance.startup_args.exported_job : this.instanceList[0]?.startup_args.exported_job ?? ''
    },
  },
  actions: {
    getInstanceList(): void {
      this.tableLoading = true
      getServing().then((res) => {
        this.instanceList = res.data
      }).catch((err) => {
        console.error(err)
      }).finally(() => {
        this.tableLoading = false
      })
    }
  }
})
