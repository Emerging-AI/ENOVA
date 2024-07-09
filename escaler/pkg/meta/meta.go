package meta

import (
	"encoding/json"
	"fmt"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/api"
)

type TaskSpecInterface interface {
	UpdateBackendConfig(result api.ConfigRecommendResult)
	GetModelConfig() ModelConfig
	GetBackendConfig() BackendConfig
	GetReplica() int
	UpdateReplica(replica int)
	GetName() string
	GetExporterServiceName() string
	GetPreferGpuNum() int
}

type ModelConfig struct {
	Llm     api.Llm `json:"llm"`
	Gpu     api.Gpu `json:"gpu"`
	Version string  `json:"version"`
}

type BackendConfig interface {
	Update(recommendResult api.ConfigRecommendResult)
}

type VllmBackendConfig struct {
	MaxNumSeqs           int     `json:"max_num_seqs"`
	TensorParallelSize   int     `json:"tensor_parallel_size"`
	GpuMemoryUtilization float32 `json:"gpu_memory_utilization"`
	VllmMode             string  `json:"vllm_mode"`
	TrustRemoteCode      bool    `json:"trust_remote_code"`
}

func (v *VllmBackendConfig) Update(recommendResult api.ConfigRecommendResult) {
	if v.MaxNumSeqs <= 0 {
		v.MaxNumSeqs = recommendResult.MaxNumSeqs
	}
	if v.TensorParallelSize <= 0 {
		v.TensorParallelSize = recommendResult.TensorParallelSize
	}
	if v.GpuMemoryUtilization <= 0 {
		v.GpuMemoryUtilization = recommendResult.GpuMemoryUtilization
	}
}

type DockerDeployRequest struct {
	Name                string
	Model               string
	Host                string
	Port                int
	Backend             string
	ExporterEndpoint    string `json:"exporter_endpoint"`
	ExporterServiceName string `json:"exporter_service_name"`
	ModelConfig         ModelConfig
	BackendConfig       map[string]interface{}
	BackendExtraConfig  map[string]string `json:"backend_extra_config"`
	Replica             int               `json:"replica"`
	Envs                []Env             `json:"envs"`
	Volumes             []Volume          `json:"volumes"`
}

type Env struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

type Volume struct {
	MountPath string `json:"mountPath"`
	HostPath  string `json:"hostPath"`
}

type TaskSpec struct {
	Name                string
	Model               string
	Host                string
	Port                int
	Backend             string
	ExporterEndpoint    string `json:"exporter_endpoint"`
	ExporterServiceName string `json:"exporter_service_name"`
	ModelConfig         ModelConfig
	BackendConfig       BackendConfig
	BackendExtraConfig  map[string]string `json:"backend_extra_config"`
	Replica             int               `json:"replica"`
	Envs                []Env             `json:"envs"`
	Gpus                string            `json:"gpus"`
	Volumes             []Volume          `json:"volumes"`
}

func (t *TaskSpec) GetName() string {
	return t.Name
}

func (t *TaskSpec) UpdateBackendConfig(result api.ConfigRecommendResult) {
	t.Replica = result.Replicas
	t.BackendConfig.Update(result)
}

func (t *TaskSpec) GetModelConfig() ModelConfig {
	return t.ModelConfig
}

func (t *TaskSpec) GetBackendConfig() BackendConfig {
	return t.BackendConfig
}

func (t *TaskSpec) GetReplica() int {
	return t.Replica
}

func (t *TaskSpec) UpdateReplica(replica int) {
	t.Replica = replica
}

func (t *TaskSpec) GetExporterServiceName() string {
	return t.ExporterServiceName
}

func (t *TaskSpec) GetPreferGpuNum() int {
	preferGpuNum := 1
	switch t.Backend {
	case "vllm":
		vllmConfig, ok := t.BackendConfig.(*VllmBackendConfig)
		if ok {
			preferGpuNum = vllmConfig.TensorParallelSize
		}
	default:
	}
	return preferGpuNum
}

func (t *TaskSpec) UnmarshalJSON(data []byte) error {
	type Alias struct {
		Name                string
		Model               string
		Host                string
		Port                int
		Backend             string
		ExporterEndpoint    string `json:"exporter_endpoint"`
		ExporterServiceName string `json:"exporter_service_name"`
		ModelConfig         ModelConfig
		Replica             int `json:"replica"`
		BackendConfig       json.RawMessage
		BackendExtraConfig  map[string]string `json:"backend_extra_config"`
		Envs                []Env             `json:"envs"`
		Gpus                string            `json:"gpus"`
		Volumes             []Volume          `json:"volumes"`
	}
	var aux Alias
	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}

	var backendConfig BackendConfig
	switch aux.Backend {
	case "vllm":
		var vllmConfig VllmBackendConfig
		if err := json.Unmarshal(aux.BackendConfig, &vllmConfig); err != nil {
			return err
		}
		backendConfig = &vllmConfig
	default:
		return fmt.Errorf("unknown backend type: %s", t.Backend)
	}
	*t = TaskSpec{
		Name:                aux.Name,
		Model:               aux.Model,
		Host:                aux.Host,
		Port:                aux.Port,
		Backend:             aux.Backend,
		ExporterEndpoint:    aux.ExporterEndpoint,
		ExporterServiceName: aux.ExporterServiceName,
		ModelConfig:         aux.ModelConfig,
		Replica:             aux.Replica,
		BackendConfig:       backendConfig,
		BackendExtraConfig:  aux.BackendExtraConfig,
		Envs:                aux.Envs,
		Gpus:                aux.Gpus,
		Volumes:             aux.Volumes,
	}
	return nil
}

type ContainerInfo struct {
	ContainerId string
	Name        string
	Status      string
}

type DetectTaskSpecResponse struct {
	TaskSpec       TaskSpec        `json:"task_spec"`
	Status         string          `json:"status"`
	ContainerInfos []ContainerInfo `json:"container_infos"`
}

type TaskDetectHistoryRequest struct {
	TaskName string `json:"task_name"`
}

type TaskDetectHistoryResponse struct {
	Data []AnomalyRecommendResult `json:"data"`
}
