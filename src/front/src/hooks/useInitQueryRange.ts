import { useExperimentStore } from '@/stores/experiment'
import { useInstanceStore } from '@/stores/instance'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import {storeToRefs} from 'pinia'

const getTestDuration = (duration: number, unit: string): number => {
  switch (unit) {
    case 'hour':
      return duration * 60 * 60
    case 'min':
      return duration * 60
    case 'sec':
      return (Math.min(duration, 10))
    default:
      return 0
  }
}

const useInitQueryRange = () => {
  const { activeExperiment } = storeToRefs(useExperimentStore())
  const { chartTimeRange, searchTimePair } = storeToRefs(useInstanceStore())
  dayjs.extend(utc)
  let startTime = new Date()
  let endTime = new Date()
  
  if (activeExperiment.value != null) {
    startTime = new Date(dayjs.utc(activeExperiment.value.create_time).toDate())
    const { duration, duration_unit } = activeExperiment.value.test_spec
    const testDuration = getTestDuration(duration, duration_unit)
    startTime.setTime(startTime.getTime())
    endTime.setTime(startTime.getTime() + (testDuration + 180) * 1000)
  } else {
    startTime.setTime(startTime.getTime() - 3600 * 1000)
  }
  const _start = dayjs(startTime).format('YYYY-MM-DD HH:mm:ss')
  const _end = dayjs(endTime).format('YYYY-MM-DD HH:mm:ss')
  
  chartTimeRange.value = [_start, _end]
  searchTimePair.value = [_start, _end]
  return { start: _start, end: _end }
}

export { useInitQueryRange }