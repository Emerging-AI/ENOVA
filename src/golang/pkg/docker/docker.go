package docker

import (
	"context"
	"enova/pkg/logger"
	"io"
	"strconv"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/network"
	"github.com/docker/docker/client"
	"github.com/docker/go-connections/nat"
)

type DockerCli struct {
	Cli *client.Client
	Ctx context.Context
}

type CreateContainerParams struct {
	ImageName     string
	Cmd           []string
	NetworkName   string
	Ports         []int
	NetworkAlias  string
	ContainerName string
	Gpus          string
	Envs          []string
	Volumes       []string
}

func (d *DockerCli) CheckOrPullImage(imageName string) {
	images, err := d.Cli.ImageList(d.Ctx, types.ImageListOptions{})
	if err != nil {
		panic(err)
	}

	imageExists := false
	for _, image := range images {
		for _, tag := range image.RepoTags {
			if tag == imageName {
				imageExists = true
				break
			}
		}
		if imageExists {
			break
		}
	}

	// 如果镜像不存在，拉取镜像
	if !imageExists {
		logger.Infof("Image %s not found. Pulling...\n", imageName)
		out, err := d.Cli.ImagePull(d.Ctx, imageName, types.ImagePullOptions{})
		if err != nil {
			panic(err)
		}
		io.Copy(io.Discard, out) // 读取拉取过程的输出以避免阻塞
		out.Close()
		logger.Infof("Image pulled successfully.")
	} else {
		logger.Infof("Image %s already exists.\n", imageName)
	}
}

func CreateHostConfig(params CreateContainerParams) *container.HostConfig {
	portBindings := nat.PortMap{}
	for _, port := range params.Ports {
		portStr := strconv.Itoa(port)
		containerPort, err := nat.NewPort("tcp", portStr)
		if err != nil {
			continue
		}
		portBindings[containerPort] = []nat.PortBinding{
			{
				HostIP:   "0.0.0.0",
				HostPort: portStr,
			},
		}
	}

	hostConfig := &container.HostConfig{
		Binds:        params.Volumes,
		NetworkMode:  container.NetworkMode(params.NetworkName),
		PortBindings: portBindings,
		IpcMode:      "host",
	}

	// TODO: add specific gpu
	if params.Gpus == "all" {
		hostConfig.DeviceRequests = []container.DeviceRequest{
			{
				Capabilities: [][]string{{"gpu"}},
				Count:        -1, // all gpus
			},
		}
	} else if params.Gpus != "" {
		hostConfig.DeviceRequests = []container.DeviceRequest{
			{
				Capabilities: [][]string{{"gpu"}},
				DeviceIDs:    []string{params.Gpus},
			},
		}
	}
	return hostConfig
}

func (d *DockerCli) CreateContainer(params CreateContainerParams) (string, error) {
	d.CheckOrPullImage(params.ImageName)

	var containerId string
	ctx := context.Background()

	hostConfig := CreateHostConfig(params)

	// 创建网络配置
	networkingConfig := &network.NetworkingConfig{
		EndpointsConfig: map[string]*network.EndpointSettings{
			params.NetworkName: {
				Aliases: []string{params.NetworkAlias},
			},
		},
	}
	resp, err := d.Cli.ContainerCreate(ctx, &container.Config{
		Image: params.ImageName,
		Cmd:   params.Cmd,
		Env:   params.Envs,
		Tty:   true,
	}, hostConfig, networkingConfig, nil, params.ContainerName)
	if err != nil {
		return containerId, err
	}

	containerId = resp.ID

	// 启动容器
	if err := d.Cli.ContainerStart(ctx, containerId, container.StartOptions{}); err != nil {
		d.Cli.ContainerRemove(d.Ctx, containerId, container.RemoveOptions{})
		return containerId, err
	}
	return containerId, nil
}

func (d *DockerCli) StopContainer(containerId string) error {
	if err := d.Cli.ContainerStop(d.Ctx, containerId, container.StopOptions{}); err != nil {
		return err
	}

	// 删除容器
	if err := d.Cli.ContainerRemove(d.Ctx, containerId, container.RemoveOptions{}); err != nil {
		return err
	}
	return nil
}

func (d *DockerCli) GetContainerStatus(containerId string) (string, error) {
	containerJSON, err := d.Cli.ContainerInspect(d.Ctx, containerId)
	if err != nil {
		return "Error", err
	}
	return containerJSON.State.Status, nil
}

func (d *DockerCli) GetContainerInfo(containerId string) (types.ContainerJSON, error) {
	containerJSON, err := d.Cli.ContainerInspect(d.Ctx, containerId)
	return containerJSON, err
}
