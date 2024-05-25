package scaler

import (
	"encoding/json"
	"errors"
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/internal/meta"
	"github.com/Emerging-AI/ENOVA/escaler/internal/resource"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/zmq"
)

type enovaServingScaler struct {
	Subscriber *zmq.ZmqSubscriber
	Client     resource.ClientInterface
}

func NewLocalDockerServingScaler() *enovaServingScaler {
	sub := zmq.ZmqSubscriber{
		Host: config.GetEConfig().Zmq.Host,
		Port: config.GetEConfig().Zmq.Port,
	}
	sub.Init()
	return &enovaServingScaler{
		Subscriber: &sub,
		Client:     resource.NewDockerResourcClient(),
	}
}

func (s *enovaServingScaler) Run() {
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

		// 执行 LocalDeploy 函数
		s.Client.DeployTask(task)
	}
}

func (s *enovaServingScaler) Stop() {

}

func (s *enovaServingScaler) RunInWaitGroup(wg *sync.WaitGroup) {
	defer wg.Done()
	s.Run()
}
