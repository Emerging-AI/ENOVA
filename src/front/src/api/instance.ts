import service from '@/utils/request'
enum API {
  ENODE = '/v1/enode',
  MONITOR = '/api/v1/query_range',
  PILOT = '/api/pilot/v1'
}

export const getEnode = () => service({
  url: API.ENODE,
  method: 'get',
});

export const addEnode = () => service({
  url: API.ENODE,
  method: 'post',
  data: {
    "instance_name": "enova_test",
    "model": "THUDM/chatglm3-6b"
  },
})

export const deleteEnode = (id: string) => service({
  url: `${API.ENODE}/${id}`,
  method: 'delete',
});

export const getExperiment = (params: string) => service({
  url: `${API.ENODE}/instance/test?${params}`,
  method: 'get',
})

export const createTest = (data: any) => service({
  url: `${API.ENODE}/instance/test`,
  method: 'post',
  data
})

const getPromUrl = (port: number) => {
  const { protocol, hostname } = window.location
  if (import.meta.env.MODE === 'development') return '/'
  return `${protocol}//${hostname}:${port}/`
}

export const getMonitorData = (params?: string) => service({
  url: `${API.MONITOR}?${params}`,
  baseURL: getPromUrl(32826),
  method: 'get',
})

export const getDetectHistory = (params?: string) => service({
  url: `${API.PILOT}/task/detect/history?${params}`,
  baseURL: getPromUrl(8183),
  method: 'get',
})