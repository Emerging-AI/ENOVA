package scaler

import (
	"encoding/json"
	"errors"
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/resource"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/zmq"
)

type EnovaServingScaler struct {
	Subscriber *zmq.ZmqSubscriber
	Client     resource.ClientInterface
	stopped    bool
}

func NewServingScaler() *EnovaServingScaler {
	if config.GetEConfig().ResourceBackend.Type == config.ResourceBackendTypeK8s {
		return NewK8sServingScaler()
	}
	return NewLocalDockerServingScaler()
}

func NewLocalDockerServingScaler() *EnovaServingScaler {
	return &EnovaServingScaler{
		Subscriber: NewZmqSubscriber(),
		Client:     resource.NewDockerResourcClient(),
		stopped:    false,
	}
}

func NewK8sServingScaler() *EnovaServingScaler {
	return &EnovaServingScaler{
		Subscriber: NewZmqSubscriber(),
		Client:     resource.Newk8sResourcClient(),
	}
}

func NewZmqSubscriber() *zmq.ZmqSubscriber {
	sub := zmq.ZmqSubscriber{
		Host: config.GetEConfig().Zmq.Host,
		Port: config.GetEConfig().Zmq.Port,
	}
	sub.Init()
	return &sub
}

func (s *EnovaServingScaler) Run() {
	if s.Subscriber == nil {
		panic(errors.New("enovaServingScaler Subscriber is nil"))
	}
	defer s.Subscriber.Close()

	for {
		// 接收消息
		logger.Infof("enovaServingScaler start Recv message")
		msg, err := s.Subscriber.Recv()
		logger.Infof("enovaServingScaler Recv message: %s", msg)
		if err != nil {
			logger.Infof("enovaServingScaler Error receiving message: %s", err)
			continue
		}
		var task meta.TaskSpec

		if err := json.Unmarshal([]byte(msg), &task); err != nil {
			logger.Errorf("enovaServingScaler Error parsing JSON response: %v, msg: %s", err, msg)
			continue
		}

		if task.Replica == 0 {
			s.Client.DeleteTask(task)
		} else {
			// 执行 LocalDeploy 函数
			s.Client.DeployTask(task)
		}
	}
}

func (s *EnovaServingScaler) Stop() {

}

func (s *EnovaServingScaler) RunInWaitGroup(wg *sync.WaitGroup) {
	defer wg.Done()
	s.Run()
}
