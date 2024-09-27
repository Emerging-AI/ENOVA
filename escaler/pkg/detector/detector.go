package detector

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/queue"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/resource"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/resource/k8s"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/api"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/redis"
)

type DetectResultManager struct {
	RedisClient *redis.RedisClient
}

func (t *DetectResultManager) AppendAnomalyResult(task meta.TaskSpec, result meta.AnomalyRecommendResult) error {
	// 使用LPUSH将新元素插入列表的左侧
	taskRecommentResultKey := fmt.Sprintf("%s_recomment_results", task.Name)
	resultBytes, _ := json.Marshal(result)
	if err := t.RedisClient.AppendListWithLimitSize(taskRecommentResultKey, string(resultBytes), 10); err != nil {
		return err
	}
	return nil
}

func (t *DetectResultManager) GetHistoricalAnomalyRecommendResult(task meta.TaskSpec) []meta.AnomalyRecommendResult {
	// 使用LPUSH将新元素插入列表的左侧
	ret := []meta.AnomalyRecommendResult{}
	taskRecommentResultKey := fmt.Sprintf("%s_recomment_results", task.Name)
	jsonArray, err := t.RedisClient.GetList(taskRecommentResultKey)
	if err != nil {
		return ret
	}

	for _, jsonItem := range jsonArray {
		var result meta.AnomalyRecommendResult
		if err := json.Unmarshal([]byte(jsonItem), &result); err != nil {
			logger.Errorf("GetHistoricalAnomalyRecommendResult Unmarshal json err: %v, jsonItem: %s ", err, jsonItem)
			continue
		}
		ret = append(ret, result)
	}
	return ret
}

type MulticlusterScaler interface {
	Scale(k8s.Workload) error
}

type Detector struct {
	Queue               *queue.InnerChanTaskQueue
	PermCli             PerformanceDetectorCli
	Client              resource.ClientInterface
	TaskMap             map[string]*meta.DetectTask
	DetectResultManager *DetectResultManager
	stopped             bool
	MulticlusterScaler  MulticlusterScaler
}

func NewDetector(ch chan meta.TaskSpecInterface) *Detector {
	// pub := zmq.ZmqPublisher{
	// 	Host: config.GetEConfig().Zmq.Host,
	// 	Port: config.GetEConfig().Zmq.Port,
	// }
	// pub.Init()
	return &Detector{
		Queue: &queue.InnerChanTaskQueue{
			Ch: ch,
		},
		PermCli: PerformanceDetectorCli{},
		TaskMap: make(map[string]*meta.DetectTask),
		Client:  resource.NewDockerResourcClient(),
		DetectResultManager: &DetectResultManager{
			RedisClient: redis.NewRedisClient(
				config.GetEConfig().Redis.Addr, config.GetEConfig().Redis.Password, config.GetEConfig().Redis.Db,
			),
		},
		stopped: false,
	}
}

func NewK8sDetector(ch chan meta.TaskSpecInterface, multiclusterScaler MulticlusterScaler) *Detector {
	// pub := zmq.ZmqPublisher{
	// 	Host: config.GetEConfig().Zmq.Host,
	// 	Port: config.GetEConfig().Zmq.Port,
	// }
	// pub.Init()
	return &Detector{
		Queue: &queue.InnerChanTaskQueue{
			Ch: ch,
		},
		PermCli: PerformanceDetectorCli{},
		TaskMap: make(map[string]*meta.DetectTask),
		Client:  resource.Newk8sResourcClient(),
		DetectResultManager: &DetectResultManager{
			RedisClient: redis.NewRedisClient(
				config.GetEConfig().Redis.Addr, config.GetEConfig().Redis.Password, config.GetEConfig().Redis.Db,
			),
		},
		stopped:            false,
		MulticlusterScaler: multiclusterScaler,
	}
}

func (d *Detector) Stop() {
	d.stopped = true
}

func (d *Detector) SendScaleTask(task meta.TaskSpecInterface) {
	d.Queue.Append(task)
	// scaleTaskJson, err := json.Marshal(task)
	// if err != nil {
	// 	logger.Errorf("DetectOnce json Marshal err: %v", err)
	// 	return
	// }

	// if ok, err := d.Publisher.Send(string(scaleTaskJson)); err != nil {
	// 	logger.Errorf("DetectOnce Publisher Send err: %v, ok: %v", err, ok)
	// 	return
	// }
}

func (d *Detector) AnomalyDetect(spec meta.TaskSpecInterface) (bool, error) {
	requestParams, err := d.PermCli.GetVllmCurrentMetricParams(spec)
	if err != nil {
		return false, err
	}
	params := api.AnomalyDetectRequest{
		Metrics:        requestParams.Metrics,
		Configurations: requestParams.Configurations,
	}
	headers := make(map[string]string)
	enovaResp, err := api.GetEnovaAlgoClient().AnomalyDetect.Call(params, headers)
	if err != nil {
		return false, err
	}

	resultData, err := json.Marshal(enovaResp.Result)
	if err != nil {
		logger.Errorf("encode resp.Result err: %v", err)
		return false, err
	}

	var anomalyDetectResp api.AnomalyDetectResponse
	if err := json.Unmarshal(resultData, &anomalyDetectResp); err != nil {
		logger.Errorf("encode AnomalyDetectResponse err: %v", err)
		return false, err
	}
	return anomalyDetectResp.IsAnomaly > 0, err
}

// DetectOneTaskSpec first Check anomaly detection, then get anomaly recovery
func (d *Detector) DetectOneTaskSpec(taskName string, taskSpec meta.TaskSpecInterface) {
	anomalyResult, err := d.AnomalyDetect(taskSpec)
	if err != nil {
		logger.Errorf("DetectOneTaskSpec AnomalyDetect get error: %v", err)
	} else {
		logger.Infof("DetectOneTaskSpec AnomalyDetect result: %v", anomalyResult)
	}
	if anomalyResult {
		requestParams, err := d.PermCli.GetVllmCurrentMetricParams(taskSpec)
		if err != nil {
			logger.Errorf("DetectOnce err: %v", err)
			return
		}
		headers := make(map[string]string)
		resp, err := api.GetEnovaAlgoClient().AnomalyRecover.Call(requestParams, headers)
		if err != nil {
			logger.Errorf("AnomalyRecover err: %v", err)
			return
		}

		resultData, err := json.Marshal(resp.Result)
		if err != nil {
			logger.Errorf("DetectOneTaskSpec encode resp.Result err: %v", err)
			return
		}

		var result api.ConfigRecommendResult
		if err := json.Unmarshal(resultData, &result); err != nil {
			logger.Errorf("DetectOneTaskSpec encode ConfigRecommendResult err: %v", err)
			return
		}

		// TODO: adapt more config
		currentConfig, ok := taskSpec.GetBackendConfig().(*meta.VllmBackendConfig)
		if !ok {
			logger.Errorf("DetectOneTaskSpec Get VllmBackendConfig failed")
			return
		}
		d.UpdateTaskSpec(taskSpec, result)
		d.SendScaleTask(taskSpec)
		d.DetectResultManager.AppendAnomalyResult(*taskSpec.(*meta.TaskSpec), meta.AnomalyRecommendResult{
			Timestamp:             time.Now().UnixMilli(),
			IsAnomaly:             anomalyResult,
			ConfigRecommendResult: result,
			CurrentConfig: api.ConfigRecommendResult{
				MaxNumSeqs:           currentConfig.MaxNumSeqs,
				TensorParallelSize:   currentConfig.TensorParallelSize,
				GpuMemoryUtilization: currentConfig.GpuMemoryUtilization,
				Replicas:             taskSpec.GetReplica(),
			},
		})
	}
}

// DetectOnce Detect anomaly from remote
// Sync Status to MulticlusterEnovaServing
func (d *Detector) DetectOnce() {
	logger.Infof("DetectOnce start detect once")
	for taskName, task := range d.TaskMap {
		if task.TaskSpec.GetScalingStrategy().Strategy == meta.StrategyAuto {
			if d.IsTaskRunning(taskName, task.TaskSpec) {
				d.DetectOneTaskSpec(taskName, task.TaskSpec)
			}
		}
	}
}

func (d *Detector) IsTaskExisted(task meta.TaskSpecInterface) bool {
	// check whether deployment is existed
	t := task.(*meta.TaskSpec)
	return d.Client.IsTaskExist(*t)
}

// IsTaskRunning TODO: add GetTaskMap
func (d *Detector) IsTaskRunning(taskName string, task meta.TaskSpecInterface) bool {
	t := task.(*meta.TaskSpec)
	if d.Client.IsTaskRunning(*t) {
		d.TaskMap[taskName].Status = meta.TaskStatusRunning
		return true
	}
	containerInfos := d.Client.GetRuntimeInfos(*t)
	for _, containerInfo := range containerInfos {
		if containerInfo.Status == "exited" {
			d.TaskMap[taskName].Status = meta.TaskStatusError
			return false
		}
	}
	d.TaskMap[taskName].Status = meta.TaskStatusScheduling
	return false
}

// UpdateTaskSpec
func (d *Detector) UpdateTaskSpec(task meta.TaskSpecInterface, resp api.ConfigRecommendResult) {
	task.UpdateBackendConfig(resp)
}

func (d *Detector) RunDetector() {
	ticker := time.NewTicker(time.Duration(config.GetEConfig().Detector.DetectInterval) * time.Second)
	for {
		if d.stopped {
			break
		}
		select {
		case <-ticker.C:
			d.DetectOnce()
		}
	}
}

func (d *Detector) DeployTask(task meta.TaskSpec) {
	if task.GetScalingStrategy().Strategy == meta.StrategyAuto {
		if err := d.UpdateServingInitialBackendConfigByRemote(&task); err != nil {
			logger.Errorf("UpdateServingInitialBackendConfigByRemote err: %v", err)
			return
		}
	}

	d.SendScaleTask(&task)
	d.RegisterTask(task)
}

// RegisterTask Register Task to taskmap
func (d *Detector) RegisterTask(task meta.TaskSpec) {
	// register at last
	d.TaskMap[task.Name] = &meta.DetectTask{
		TaskSpec: &task,
		Status:   meta.TaskStatusCreated,
	}
}

func (d *Detector) DeleteTask(taskName string) {
	task, ok := d.TaskMap[taskName]
	if !ok {
		logger.Infof("taskName: %s is not register", taskName)
		return
	}
	delete(d.TaskMap, taskName)
	task.TaskSpec.UpdateReplica(0)
	d.SendScaleTask(task.TaskSpec)
}

// UpdateServingngInitialBackendConfigByRemote Get Remote recommending backendCOnfig When first deploy,
func (d *Detector) UpdateServingInitialBackendConfigByRemote(spec meta.TaskSpecInterface) error {
	params := api.ConfigRecommendRequest{
		Llm: spec.GetModelConfig().Llm,
		Gpu: spec.GetModelConfig().Gpu,
	}
	headers := make(map[string]string)
	resp, err := api.GetEnovaAlgoClient().ConfigRecommend.Call(params, headers)
	if err != nil {
		return err
	}

	resultData, err := json.Marshal(resp.Result)
	if err != nil {
		logger.Errorf("encode resp.Result err: %v", err)
		return err
	}

	var result api.ConfigRecommendResult
	if err := json.Unmarshal(resultData, &result); err != nil {
		logger.Errorf("encode ConfigRecommendResult err: %v", err)
		return err
	}
	spec.UpdateBackendConfig(result)
	return nil
}
