import axios, { type AxiosResponse } from 'axios'

const service = axios.create({
  baseURL: '/',
  timeout: 10000
})

service.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

service.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    if (Number(res.code) === 0 || res.status === 'success') {
      return res.code === 0 ? res.result : res
    } else {
      ElMessage({
        message: res.response?.data?.message || res.message || 'Error',
        type: 'error',
        duration: 5 * 1000
      })
      return Promise.reject(res)
    }
  },
  (error) => {
    ElMessage({
      message: error.response?.data?.message || error.message || 'Error',
      type: 'error',
      duration: 5 * 1000
    })
    return Promise.reject(error)
  }
)

export default service
