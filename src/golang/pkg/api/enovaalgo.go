package api

import (
	"enova/pkg/config"
	"fmt"
	"sync"
)

var enovaAlgoInitOnce sync.Once

type enovaAlgoClient struct {
	ConfigRecommend HttpApi
	AnomalyDetect   HttpApi
	AnomalyRecover  HttpApi
}

type ConfigRecommendRequest struct {
	Llm struct {
		Framework string  `json:"framework"`
		Param     float32 `json:"param"`
	} `json:"llm"`
	Gpu struct {
		Name string `json:"name"`
		Spec int    `json:"spec"`
		Num  int    `json:"num"`
	} `json:"gpu"`
}

type ConfigRecommendResult struct {
	MaxNumSeqs           int     `json:"max_num_seqs"`
	TensorParallelSize   int     `json:"tensor_parallel_size"`
	GpuMemoryUtilization float32 `json:"gpu_memory_utilization"`
	Replicas             int     `json:"replicas"`
}

type Llm struct {
	Framework string  `json:"framework"`
	Param     float32 `json:"param"`
}

type Gpu struct {
	Name string `json:"name"`
	Spec int    `json:"spec"`
	Num  int    `json:"num"`
}

type MetricValue [2]float64

type Metrics struct {
	ActiveRequests        []MetricValue `json:"active_requests"`
	RunningRequests       []MetricValue `json:"running_requests"`
	PendingRequests       []MetricValue `json:"pending_requests"`
	GPUKVCacheUsage       []MetricValue `json:"gpu_kv_cache_usage"`
	ServerNewRequests     []MetricValue `json:"server_new_requests"`
	ServerSuccessRequests []MetricValue `json:"server_success_requests"`
}

type Configurations struct {
	MaxNumSeqs           int     `json:"max_num_seqs"`
	TensorParallelSize   int     `json:"tensor_parallel_size"`
	GPUMemoryUtilization float32 `json:"gpu_memory_utilization"`
	Replicas             int     `json:"replicas"`
}

type AnomalyRecoverRequest struct {
	Metrics        []Metrics      `json:"metrics"`
	Configurations Configurations `json:"configurations"`
	Llm            Llm            `json:"llm"`
	Gpu            Gpu            `json:"gpu"`
}

type AnomalyDetectRequest struct {
	Metrics        []Metrics      `json:"metrics"`
	Configurations Configurations `json:"configurations"`
}

type AnomalyDetectResponse struct {
	IsAnomaly int `json:"is_anomaly"`
}

var EnovaAlgoClient *enovaAlgoClient

func GetEnovaAlgoClient() *enovaAlgoClient {
	enovaAlgoInitOnce.Do(func() {
		EnovaAlgoClient = &enovaAlgoClient{
			ConfigRecommend: HttpApi{
				Method: "POST",
				Url:    fmt.Sprintf("http://%s/api/enovaalgo/v1/config_recommend", config.GetEConfig().EnovaAlgo.Host),
			},
			AnomalyDetect: HttpApi{
				Method: "POST",
				Url:    fmt.Sprintf("http://%s/api/enovaalgo/v1/anomaly_detect", config.GetEConfig().EnovaAlgo.Host),
			},
			AnomalyRecover: HttpApi{
				Method: "POST",
				Url:    fmt.Sprintf("http://%s/api/enovaalgo/v1/anomaly_recover", config.GetEConfig().EnovaAlgo.Host),
			},
		}
	})
	return EnovaAlgoClient
}
