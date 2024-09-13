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
	GetScalingStrategy() ScalingStrategy
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

type DeployRequest struct {
	Name                string
	Model               string
	Host                string
	Port                int
	Backend             string
	Image               string
	ExporterEndpoint    string `json:"exporter_endpoint"`
	ExporterServiceName string `json:"exporter_service_name"`
	ModelConfig         ModelConfig
	BackendConfig       map[string]interface{}
	BackendExtraConfig  map[string]string `json:"backend_extra_config"`
	Replica             int               `json:"replica"`
	Envs                []Env             `json:"envs"`
	Volumes             []Volume          `json:"volumes"`
	Namespace           string            `json:"namespace"`
	NodeSelector        map[string]string `json:"node_selector"`
	Ingress             Ingress           `json:"ingress"`
	Service             Service           `json:"service"`
	Resources           Resources         `json:"resources"`
	ScalingStrategy     ScalingStrategy   `json:"scaling_strategy"`
	Collector           CollectorConfig   `json:"collector"`
}

type Env struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

type Volume struct {
	MountPath string `json:"mountPath"`
	HostPath  string `json:"hostPath"`
}

type Raw struct{}

type Ingress struct {
	Name  string `json:"name"`
	Paths []Path `json:"paths"`
	Raw   Raw    `json:"raw"`
}

type Path struct {
	Path    string  `json:"path"`
	Backend Backend `json:"backend"`
}

type Backend struct {
	Service ServiceDetail `json:"service"`
}

type ServiceDetail struct {
	Name string `json:"name"`
	Port Port   `json:"port"`
}

type Port struct {
	Number int32 `json:"number"`
}

type Service struct {
	Name  string `json:"name"`
	Ports []Port `json:"ports"`
	Raw   Raw    `json:"raw"`
}

type Resources struct {
	GPU     string `json:"gpu"`
	GPUType string `json:"gpu_type"`
}

type Strategy string

const (
	StrategyManual = "manual"
	StrategyAuto   = "auto"
)

type ScalingStrategy struct {
	// +optional
	Strategy string `json:"strategy,omitempty"`
}

type KafkaConfig struct {
	Brokers  []string
	Username string
	Password string
}

type CollectorConfig struct {
	Enable    bool
	ClusterId string
	Kafka     KafkaConfig
}

type TaskSpec struct {
	Name                string
	Model               string
	Host                string
	Port                int
	Image               string
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
	Namespace           string            `json:"namespace"`
	NodeSelector        map[string]string `json:"node_selector"`
	Ingress             Ingress           `json:"ingress"`
	Service             Service           `json:"service"`
	Resources           Resources         `json:"resources"`
	ScalingStrategy     ScalingStrategy   `json:"scaling_strategy"`
	Collector           CollectorConfig   `json:"collector"`
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
		Image               string
		ExporterEndpoint    string `json:"exporter_endpoint"`
		ExporterServiceName string `json:"exporter_service_name"`
		ModelConfig         ModelConfig
		Replica             int `json:"replica"`
		BackendConfig       json.RawMessage
		BackendExtraConfig  map[string]string `json:"backend_extra_config"`
		Envs                []Env             `json:"envs"`
		Gpus                string            `json:"gpus"`
		Volumes             []Volume          `json:"volumes"`
		Namespace           string            `json:"namespace"`
		NodeSelector        map[string]string `json:"node_selector"`
		Ingress             Ingress           `json:"ingress"`
		Service             Service           `json:"service"`
		Resources           Resources         `json:"resources"`
		ScalingStrategy     ScalingStrategy   `json:"scaling_strategy"`
		Collector           CollectorConfig   `json:"collector"`
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
		Image:               aux.Image,
		ExporterEndpoint:    aux.ExporterEndpoint,
		ExporterServiceName: aux.ExporterServiceName,
		ModelConfig:         aux.ModelConfig,
		Replica:             aux.Replica,
		BackendConfig:       backendConfig,
		BackendExtraConfig:  aux.BackendExtraConfig,
		Envs:                aux.Envs,
		Gpus:                aux.Gpus,
		Volumes:             aux.Volumes,
		Namespace:           aux.Namespace,
		NodeSelector:        aux.NodeSelector,
		Ingress:             aux.Ingress,
		Service:             aux.Service,
		Resources:           aux.Resources,
		ScalingStrategy:     aux.ScalingStrategy,
		Collector:           aux.Collector,
	}
	return nil
}

func (t *TaskSpec) GetScalingStrategy() ScalingStrategy {
	return t.ScalingStrategy
}

type RuntimeInfo struct {
	ContainerId string
	Name        string
	Status      string
}

type DetectTaskSpecResponse struct {
	TaskSpec       TaskSpec      `json:"task_spec"`
	Status         string        `json:"status"`
	ContainerInfos []RuntimeInfo `json:"container_infos"`
}

type TaskDetectHistoryRequest struct {
	TaskName string `json:"task_name"`
}

type TaskDetectHistoryResponse struct {
	Data []AnomalyRecommendResult `json:"data"`
}
