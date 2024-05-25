package detector

import (
	"encoding/json"
	"fmt"
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/internal/meta"

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

func NewDetectorServer() *DetectorServer {
	detector := NewDetector()
	detectorServer := DetectorServer{
		Detector: detector,
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

type DockerDeployResource struct {
	server.BaseResource
	Detector *Detector
}

func (r DockerDeployResource) Path() string {
	return "/docker/deploy"
}

// Post godoc
// @Summary      Create alert policy object
// @Tags         task
// @Accept       json
// @Produce      json
// @Param  		 payload body meta.DockerDeployRequest true "request content"
// @Success      200  {string}  "success"
// @Router       /api/escaler/v1/docker/deploy [post]
func (r DockerDeployResource) Post(c *gin.Context) {
	var dockerDeployRequest meta.DockerDeployRequest
	if err := c.ShouldBindJSON(&dockerDeployRequest); err != nil {
		r.SetErrorResult(c, api.EnvoaResponse{
			Message: fmt.Sprintf("参数解析失败：%s", err),
			Code:    400100,
			Version: config.GetEConfig().Detector.Api.Version,
		})
		return
	}

	var taskSpec meta.TaskSpec
	if dockerDeployRequest.Backend == "vllm" {
		var vllmConfig meta.VllmBackendConfig

		resultData, err := json.Marshal(dockerDeployRequest.BackendConfig)
		if err != nil {
			logger.Errorf("encode dockerDeployRequest.BackendConfig err: %v", err)
			return
		}

		if err := json.Unmarshal(resultData, &vllmConfig); err != nil {
			logger.Errorf("encode VllmBackendConfig err: %v", err)
			return
		}
		exporterServiceName := fmt.Sprintf("%s-%s-%s", config.GetEConfig().Enode.Name, dockerDeployRequest.ModelConfig.Llm.Framework, dockerDeployRequest.ModelConfig.Version)

		taskSpec = meta.TaskSpec{
			Name:                dockerDeployRequest.Name,
			Model:               dockerDeployRequest.Model,
			Host:                dockerDeployRequest.Host,
			Port:                dockerDeployRequest.Port,
			Backend:             dockerDeployRequest.Backend,
			ExporterEndpoint:    dockerDeployRequest.ExporterEndpoint,
			ExporterServiceName: exporterServiceName,
			ModelConfig:         dockerDeployRequest.ModelConfig,
			BackendConfig:       &vllmConfig,
			BackendExtraConfig:  dockerDeployRequest.BackendExtraConfig,
			Replica:             dockerDeployRequest.Replica,
			Envs:                dockerDeployRequest.Envs,
			Gpus:                "all",
			Volumes:             dockerDeployRequest.Volumes,
		}
	}

	r.Detector.RegisterTask(taskSpec)
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
func (r DockerDeployResource) Get(c *gin.Context) {
	taskName := c.Query("task_name")
	detectTask, ok := r.Detector.TaskMap[taskName]
	if !ok {
		r.SetErrorResult(c, fmt.Errorf("taskName: %s, can not be found", taskName))
	} else {
		taskSpec := detectTask.TaskSpec.(*meta.TaskSpec)
		containerInfos := r.Detector.Client.GetContainerinfos(*taskSpec)

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
func (r DockerDeployResource) Delete(c *gin.Context) {
	taskName := c.Query("task_name")
	r.Detector.DeleteTask(taskName)
	r.SetResult(c, "Success")
}

func (d *DetectorServer) InitServer() {
	middlewares := make([]gin.HandlerFunc, 0)

	resources := make([]interface{}, 0)
	resources = append(resources, DockerDeployResource{
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
