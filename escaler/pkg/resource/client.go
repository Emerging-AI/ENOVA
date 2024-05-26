package resource

import (
	"bufio"
	"context"
	"os/exec"
	"strings"

	"encoding/json"
	"fmt"
	"strconv"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/docker"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/redis"

	"github.com/docker/docker/client"
	"github.com/google/uuid"
)

type TaskManager struct {
	RedisClient *redis.RedisClient
}

func (t *TaskManager) GetTaskContainerIds(task meta.TaskSpec) ([]string, bool) {
	containerIds, err := t.RedisClient.GetList(task.Name)
	if err != nil {
		logger.Infof("GetList err: %v", err)
		return []string{}, false
	}
	return containerIds, true
}

func (t *TaskManager) SetTaskContainerIds(task meta.TaskSpec, containerIds []string) error {
	return t.RedisClient.SetList(task.Name, containerIds)
}

func (t *TaskManager) DeleteTaskContainerIds(task meta.TaskSpec) {
	_, err := t.RedisClient.DelList(task.Name)
	if err != nil {
		logger.Errorf("DeleteTaskContainerIds err: %v", err)
	}
}

type ClientInterface interface {
	DeployTask(spec meta.TaskSpec)
	DeleteTask(spec meta.TaskSpec)
	IsTaskRunning(spec meta.TaskSpec) bool
	GetContainerinfos(spec meta.TaskSpec) []meta.ContainerInfo
}

type ContainerIds []string

type GpuStatsInfo struct {
	GpuId  int
	Status string
}

func GetGpuStats() ([]*GpuStatsInfo, error) {
	cmd := exec.Command("nvidia-smi", "--query-gpu=index", "--format=csv,noheader,nounits")
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	var gpus []*GpuStatsInfo

	for scanner.Scan() {
		line := scanner.Text()

		gpuId, err := strconv.Atoi(line)
		if err != nil {
			return nil, err
		}

		gpus = append(gpus, &GpuStatsInfo{
			GpuId:  gpuId,
			Status: "Available",
		})
	}

	return gpus, nil
}

type DockerResourceClient struct {
	DockerClient       *docker.DockerCli
	TaskManager        *TaskManager
	ContainerIDGpusMap map[string][]string
	LocalGpuStats      []*GpuStatsInfo
}

func (d *DockerResourceClient) DeployTask(spec meta.TaskSpec) {
	d.LocalDeploy(spec)
}

func (d *DockerResourceClient) DeleteTask(spec meta.TaskSpec) {

}

func (d *DockerResourceClient) LocalDeploy(task meta.TaskSpec) {
	logger.Infof("start local deploy, Replica: %d", task.Replica)
	d.DeployByDocker(task)
}

func (d *DockerResourceClient) CreateContainerName(prefix string) string {
	u := uuid.New()
	return fmt.Sprintf("%s-replica-%s", prefix, u.String()[:4])
}

func (d *DockerResourceClient) DeployByDocker(task meta.TaskSpec) {
	containerIds, ok := d.TaskManager.GetTaskContainerIds(task)
	logger.Infof("DeployByDocker GetTaskContainerIds taskName: %s, containerIds: %v", task.Name, containerIds)
	if !ok {
		for i := 0; i < task.Replica; i++ {
			containerID, err := d.singleDeployByDocker(&task)
			if err != nil {
				logger.Errorf("DeployByDocker err: %v", err)
			} else {
				logger.Infof("sucees deploy task: %v, containerId: %s", task, containerID)
				containerIds = append(containerIds, containerID)
			}
		}
		d.TaskManager.SetTaskContainerIds(task, containerIds)
	} else {
		// delete all container when replica = 0
		if task.Replica == 0 {
			for _, containerId := range containerIds {
				if err := d.DeleteSingleEnode(containerId); err != nil {
					logger.Errorf("DeleteSingleEnode containerId: %s, err: %v", containerId, err)
				}
				gpuStrList := d.ContainerIDGpusMap[containerId]
				for _, gpuIdStr := range gpuStrList {
					gpuId, err := strconv.Atoi(gpuIdStr)
					if err != nil {
						logger.Errorf("reset GpuStat error, containerId: %s, err: %v", containerId, err)
					}
					for _, gpuStat := range d.LocalGpuStats {
						if gpuStat.GpuId == gpuId {
							gpuStrList = append(gpuStrList, fmt.Sprintf("%d", gpuStat.GpuId))
							gpuStat.Status = "Available"
							break
						}
					}
				}
				delete(d.ContainerIDGpusMap, containerId)
			}
			d.TaskManager.DeleteTaskContainerIds(task)
		} else {
			// first checkout replica number
			// second scale up or down when replica is not match
			if len(containerIds) > task.Replica {
				removeCnt := len(containerIds) - task.Replica
				logger.Infof("start to scale down task: %s, removeCnt: %d", task.Name, removeCnt)
				for i := 0; i < removeCnt; i++ {
					containerId := containerIds[i]
					if err := d.DeleteSingleEnode(containerId); err != nil {
						logger.Errorf("DeleteSingleEnode containerId: %s, err: %v", containerIds[0], err)
					}
					gpuStrList := d.ContainerIDGpusMap[containerId]
					for _, gpuIdStr := range gpuStrList {
						gpuId, err := strconv.Atoi(gpuIdStr)
						if err != nil {
							logger.Errorf("reset GpuStat error, containerId: %s, err: %v", containerId, err)
						}
						for _, gpuStat := range d.LocalGpuStats {
							if gpuStat.GpuId == gpuId {
								gpuStrList = append(gpuStrList, fmt.Sprintf("%d", gpuStat.GpuId))
								gpuStat.Status = "Available"
								break
							}
						}
					}
				}
				containerIds = containerIds[removeCnt:]
				// d.TaskContainerIdMap[task.Name] = d.TaskContainerIdMap[task.Name][removeCnt:]
			} else if len(containerIds) < task.Replica {
				scaleoutCnt := task.Replica - len(containerIds)
				logger.Infof("start to scale up task: %s, scaleoutCnt: %d", task.Name, scaleoutCnt)
				for i := 0; i < scaleoutCnt; i++ {
					// Record Gpu
					containerID, err := d.singleDeployByDocker(&task)
					if err != nil {
						logger.Errorf("DeployByDocker err: %v", err)
					} else {
						logger.Infof("sucees deploy task: %v, containerId: %s", task, containerID)
						containerIds = append(containerIds, containerID)
					}
				}
			}
			d.TaskManager.SetTaskContainerIds(task, containerIds)
		}
	}
}

func (d *DockerResourceClient) singleDeployByDocker(task *meta.TaskSpec) (string, error) {
	selectGpuNum := 0
	preferGpuNum := task.GetPreferGpuNum()
	gpuStrList := []string{}
	logger.Infof("before deploy d.LocalGpuStats: %v", d.LocalGpuStats)
	for _, gpuStat := range d.LocalGpuStats {
		if gpuStat.Status == "Available" {
			gpuStrList = append(gpuStrList, fmt.Sprintf("%d", gpuStat.GpuId))
			selectGpuNum += 1
			gpuStat.Status = "InUsed"
		}
		if selectGpuNum >= preferGpuNum {
			break
		}
	}
	logger.Infof("after deploy d.LocalGpuStats: %v, gpuStrList: %v", d.LocalGpuStats, gpuStrList)
	task.Gpus = strings.Join(gpuStrList, ",")
	containerID, err := d.CreateSingleEnode(*task, d.CreateContainerName(task.ExporterServiceName))
	if err != nil {
		logger.Errorf("singleDeployByDocker err: %v", err)
	} else {
		d.ContainerIDGpusMap[containerID] = gpuStrList
	}
	return containerID, err
}

func (d *DockerResourceClient) CreateSingleEnode(spec meta.TaskSpec, containerName string) (string, error) {
	cmd := []string{
		"enova", "enode", "run", "--model", spec.Model, "--port", strconv.Itoa(spec.Port), "--host", spec.Host,
		"--backend", spec.Backend,
		"--exporter_endpoint", spec.ExporterEndpoint,
		"--exporter_service_name", containerName,
	}

	vllmBackendConfig, ok := spec.BackendConfig.(*meta.VllmBackendConfig)
	if ok {
		jsonBytes, err := json.Marshal(vllmBackendConfig)
		if err != nil {

		} else {
			var vllmBackendConfigMap map[string]interface{}
			err = json.Unmarshal(jsonBytes, &vllmBackendConfigMap)
			if err != nil {

			} else {
				for k, v := range vllmBackendConfigMap {
					cmd = append(cmd, []string{fmt.Sprintf("--%s", k), fmt.Sprintf("%v", v)}...)
				}
			}

		}
	}
	// Add extra enode params
	for k, v := range spec.BackendExtraConfig {
		cmd = append(cmd, []string{fmt.Sprintf("--%s", k), fmt.Sprintf("%v", v)}...)
	}
	params := docker.CreateContainerParams{
		ImageName:     config.GetEConfig().Enode.Image,
		Cmd:           cmd,
		NetworkName:   config.GetEConfig().Enode.Network,
		Ports:         []int{spec.Port},
		NetworkAlias:  config.GetEConfig().Enode.NetworkAlias,
		ContainerName: containerName,
		Envs:          d.BuildDockerEnvs(spec.Envs),
		Gpus:          spec.Gpus,
		Volumes:       d.BuildDockerVolumes(spec.Volumes),
	}
	return d.DockerClient.CreateContainer(params)
}

func (d *DockerResourceClient) BuildDockerEnvs(envs []meta.Env) []string {
	ret := []string{}
	for _, e := range envs {
		ret = append(ret, fmt.Sprintf("%s=%s", e.Name, e.Value))
	}
	return ret
}

func (d *DockerResourceClient) BuildDockerVolumes(volumes []meta.Volume) []string {
	ret := []string{}
	for _, e := range volumes {
		ret = append(ret, fmt.Sprintf("%s:%s", e.HostPath, e.MountPath))
	}
	return ret
}

func (d *DockerResourceClient) DeleteSingleEnode(containerId string) error {
	return d.DockerClient.StopContainer(containerId)
}

// IsTaskRunning: check all containers running
func (d *DockerResourceClient) IsTaskRunning(task meta.TaskSpec) bool {
	containerIds, ok := d.TaskManager.GetTaskContainerIds(task)
	if !ok {
		logger.Infof("IsTaskRunning GetTaskContainerIds failed")
		return false
	}
	ret := false
	for _, containerId := range containerIds {
		status, err := d.DockerClient.GetContainerStatus(containerId)
		if err != nil {
			logger.Errorf("IsTaskRunning GetContainerStatus error: %v", err)
			ret = false
		}
		logger.Infof("IsTaskRunning GetContainerStatus, taskName: %s, containerId: %s, status: %s", task.Name, containerId, status)
		if status == "running" {
			ret = true
		} else {
			ret = false
		}
	}
	return ret
}

func (d *DockerResourceClient) GetContainerinfos(spec meta.TaskSpec) []meta.ContainerInfo {
	ret := []meta.ContainerInfo{}
	containerIds, ok := d.TaskManager.GetTaskContainerIds(spec)
	if !ok {
		logger.Infof("GetTaskInfo GetTaskContainerIds failed")
		return ret
	}
	for _, containerId := range containerIds {
		containerJson, err := d.DockerClient.GetContainerInfo(containerId)
		if err != nil {
			logger.Errorf("IsTaskRunning GetContainerStatus error: %v", err)
			continue
		}
		ret = append(ret, meta.ContainerInfo{
			Name:        containerJson.Name,
			ContainerId: containerId,
			Status:      containerJson.State.Status,
		})
	}
	return ret
}

func NewDockerResourcClient() *DockerResourceClient {
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		panic(err)
	}

	dockerCli := docker.DockerCli{
		Cli: cli,
		Ctx: context.Background(),
	}
	localGpuStats, err := GetGpuStats()
	if err != nil {
		logger.Errorf("DockerResourceClient GetGpuStats err: %v", err)
	}
	return &DockerResourceClient{
		DockerClient: &dockerCli,
		TaskManager: &TaskManager{
			RedisClient: redis.NewRedisClient(),
		},
		ContainerIDGpusMap: make(map[string][]string),
		LocalGpuStats:      localGpuStats,
	}
}
