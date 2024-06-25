import { defineStore } from 'pinia'
import { getExperiment } from '@/api/instance'
import type { ExperimentType } from './config'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
interface ExperimentStoreState {
  testList: ExperimentType[]
  currentId: string
  drawerVisible: boolean
}

interface ExperimentRes {
  data: ExperimentType[]
  page: number
  size: number
  total_num: number
  total_page: number
  page_size: number
}

export const useExperimentStore = defineStore('experiment', {
  state: (): ExperimentStoreState => ({
    testList: [],
    currentId: '',
    drawerVisible: false
  }),
  getters: {
    activeExperiment: (state): ExperimentType | undefined => {
      return state.testList.find((item) => item.test_id === state.currentId) || undefined
    }
  },
  actions: {
    getTestList(params: string) {
      dayjs.extend(utc)
      return new Promise<ExperimentRes>((resolve, reject) => {
        getExperiment(params)
          .then((res) => {
            this.testList =
              res.data.length > 0
                ? res.data.map((i: ExperimentType) => {
                    return {
                      ...i,
                      create_time: dayjs.utc(i.create_time).toDate()
                    }
                  })
                : []
            resolve(res as unknown as ExperimentRes)
          })
          .catch(() => {
            reject(null)
          })
      })
    }
  }
})
