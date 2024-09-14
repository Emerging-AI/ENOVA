package detector

import (
	"encoding/json"
	"fmt"
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/api"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/httpserver/server"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"

	"github.com/gin-gonic/gin"
)

type DetectorServer struct {
	Detector *Detector
	server   *server.APIServer
}

func NewDetectorServer(
	ch chan meta.TaskSpecInterface,
	statusSyncer StatusSyncer,
	multiclusterScaler MulticlusterScaler) *DetectorServer {

	detectorServer := DetectorServer{}
	if config.GetEConfig().ResourceBackend.Type == config.ResourceBackendTypeK8s {
		detector := NewK8sDetector(ch, statusSyncer, multiclusterScaler)
		detectorServer.Detector = detector
	} else {
		detector := NewDetector(ch)
		detectorServer.Detector = detector
	}

	detectorServer.InitServer()
	return &detectorServer
}

type DockerDeployRequest struct {
	Name        string           `json:"name"`
	Model       string           `json:"model"`
	ModelConfig meta.ModelConfig `json:"model_config"`
}

type TaskDetectResource struct {
	server.BaseResource
	Detector *Detector
}

func (r TaskDetectResource) Path() string {
	return "/task/detect/history"
}

// Get godoc
// @Summary      Get task detect history list
// @Tags         task
// @Accept       json
// @Produce      json
// @Param        task_name      query  string false "Task Name"
// @Success      200  {object}  	meta.TaskDetectHistoryResponse
// @Router       /api/escaler/v1/task/detect/history [get]
func (r TaskDetectResource) Get(c *gin.Context) {
	taskName := c.Query("task_name")
	detectTask, ok := r.Detector.TaskMap[taskName]
	if !ok {
		r.SetErrorResult(c, fmt.Errorf("taskName: %s, can not be found", taskName))
	} else {
		taskSpec := detectTask.TaskSpec.(*meta.TaskSpec)
		r.SetResult(c, meta.TaskDetectHistoryResponse{
			Data: r.Detector.DetectResultManager.GetHistoricalAnomalyRecommendResult(*taskSpec),
		})
	}
}

type DeployResource struct {
	server.BaseResource
	Detector *Detector
}

func (r DeployResource) Path() string {
	return "/deploy"
}

// Post godoc
// @Summary      Create alert policy object
// @Tags         task
// @Accept       json
// @Produce      json
// @Param  		 payload body meta.DockerDeployRequest true "request content"
// @Success      200  {string}  "success"
// @Router       /api/escaler/v1/deploy [post]
func (r DeployResource) Post(c *gin.Context) {
	var deployRequest meta.DeployRequest
	if err := c.ShouldBindJSON(&deployRequest); err != nil {
		r.SetErrorResult(c, api.EnvoaResponse{
			Message: fmt.Sprintf("参数解析失败：%s", err),
			Code:    400100,
			Version: config.GetEConfig().Detector.Api.Version,
		})
		return
	}

	logger.Infof("Get deployRequest: %v", deployRequest)
	var taskSpec meta.TaskSpec
	if deployRequest.Backend == "vllm" {
		var vllmConfig meta.VllmBackendConfig

		resultData, err := json.Marshal(deployRequest.BackendConfig)
		if err != nil {
			logger.Errorf("encode deployRequest.BackendConfig err: %v", err)
			return
		}

		if err := json.Unmarshal(resultData, &vllmConfig); err != nil {
			logger.Errorf("encode VllmBackendConfig err: %v", err)
			return
		}
		exporterServiceName := fmt.Sprintf("%s-%s-%s", config.GetEConfig().Serving.Name, deployRequest.ModelConfig.Llm.Framework, deployRequest.ModelConfig.Version)

		taskSpec = meta.TaskSpec{
			Name:                deployRequest.Name,
			Model:               deployRequest.Model,
			Host:                deployRequest.Host,
			Port:                deployRequest.Port,
			Backend:             deployRequest.Backend,
			ExporterEndpoint:    deployRequest.ExporterEndpoint,
			ExporterServiceName: exporterServiceName,
			ModelConfig:         deployRequest.ModelConfig,
			BackendConfig:       &vllmConfig,
			BackendExtraConfig:  deployRequest.BackendExtraConfig,
			Replica:             deployRequest.Replica,
			Envs:                deployRequest.Envs,
			Gpus:                "all",
			Volumes:             deployRequest.Volumes,
			Namespace:           deployRequest.Namespace,
			NodeSelector:        deployRequest.NodeSelector,
			Ingress:             deployRequest.Ingress,
			Service:             deployRequest.Service,
			Resources:           deployRequest.Resources,
			ScalingStrategy:     deployRequest.ScalingStrategy,
			Collector:           deployRequest.Collector,
		}
	}

	if deployRequest.Image != "" {
		taskSpec.Image = deployRequest.Image
	}

	r.Detector.DeployTask(taskSpec)
	r.SetResult(c, "Success")
}

// Get godoc
// @Summary      Get docker task info
// @Tags         task
// @Accept       json
// @Produce      json
// @Param        task_name      query  string false "Task Name"
// @Success      200  {object}  	meta.DetectTaskSpecResponse
// @Router       /api/escaler/v1/docker/deploy [get]
func (r DeployResource) Get(c *gin.Context) {
	taskName := c.Query("task_name")
	detectTask, ok := r.Detector.TaskMap[taskName]
	if !ok {
		r.SetErrorResult(c, fmt.Errorf("taskName: %s, can not be found", taskName))
	} else {
		taskSpec := detectTask.TaskSpec.(*meta.TaskSpec)
		containerInfos := r.Detector.Client.GetRuntimeInfos(*taskSpec)

		// compute current detect task status
		for _, containerInfo := range containerInfos {
			if containerInfo.Status == "running" {
				detectTask.Status = meta.TaskStatusRunning
			}
		}
		r.SetResult(c, meta.DetectTaskSpecResponse{
			TaskSpec:       *taskSpec,
			Status:         string(detectTask.Status),
			ContainerInfos: containerInfos,
		})
	}
}

// Get godoc
// @Summary      Delete docker task
// @Tags         task
// @Accept       json
// @Produce      json
// @Param        task_name      query  string false "Task Name"
// @Success      200  {string}  "Success"
// @Router       /api/escaler/v1/docker/deploy [delete]
func (r DeployResource) Delete(c *gin.Context) {
	taskName := c.Query("task_name")
	r.Detector.DeleteTask(taskName)
	r.SetResult(c, "Success")
}

func (d *DetectorServer) InitServer() {
	middlewares := make([]gin.HandlerFunc, 0)

	resources := make([]interface{}, 0)
	resources = append(resources, DeployResource{
		Detector: d.Detector,
	})
	resources = append(resources, TaskDetectResource{
		Detector: d.Detector,
	})

	// 启动web服务
	s := server.APIServer{
		Middlewares: middlewares,
		Resources:   resources,
	}
	d.server = &s
	s.InitAPIServer()
}

func (d *DetectorServer) RunServer() {
	// 初始化通知配置
	d.server.Run()

}

func (d *DetectorServer) Run() {
	go d.Detector.RunDetector()
	d.RunServer()
}

func (d *DetectorServer) RunInWaitGroup(wg *sync.WaitGroup) {
	defer wg.Done()
	d.Run()
}

func (d *DetectorServer) GetEngine() *gin.Engine {
	return d.server.GetEngine()
}
