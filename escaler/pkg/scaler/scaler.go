package scaler

import (
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/queue"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/resource"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/zmq"
)

type EnovaServingScaler struct {
	// Subscriber *zmq.ZmqSubscriber
	Queue   *queue.InnerChanTaskQueue
	Client  resource.ClientInterface
	stopped bool
}

func NewServingScaler(ch chan meta.TaskSpecInterface) *EnovaServingScaler {
	if config.GetEConfig().ResourceBackend.Type == config.ResourceBackendTypeK8s {
		return NewK8sServingScaler(ch)
	}
	return NewLocalDockerServingScaler(ch)
}

func NewLocalDockerServingScaler(ch chan meta.TaskSpecInterface) *EnovaServingScaler {
	return &EnovaServingScaler{
		Queue: &queue.InnerChanTaskQueue{
			Ch: ch,
		},
		Client:  resource.NewDockerResourcClient(),
		stopped: false,
	}
}

func NewK8sServingScaler(ch chan meta.TaskSpecInterface) *EnovaServingScaler {
	return &EnovaServingScaler{
		Queue: &queue.InnerChanTaskQueue{
			Ch: ch,
		},
		Client: resource.Newk8sResourcClient(),
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
	// if s.Subscriber == nil {
	// 	panic(errors.New("enovaServingScaler Subscriber is nil"))
	// }
	// defer s.Subscriber.Close()

	for {
		// 接收消息
		logger.Infof("enovaServingScaler start Recv message")
		task, ok := s.Queue.Pop()
		if !ok {
			continue
		}
		// logger.Infof("enovaServingScaler Recv message: %s", msg)
		// if err != nil {
		// 	logger.Infof("enovaServingScaler Error receiving message: %s", err)
		// 	continue
		// }
		acutalTask := task.(*meta.TaskSpec)

		// if err := json.Unmarshal([]byte(msg), &task); err != nil {
		// 	logger.Errorf("enovaServingScaler Error parsing JSON response: %v, msg: %s", err, msg)
		// 	continue
		// }

		if acutalTask.Replica == 0 {
			s.Client.DeleteTask(*acutalTask)
		} else {
			// 执行 LocalDeploy 函数
			s.Client.DeployTask(*acutalTask)
		}
	}
}

func (s *EnovaServingScaler) Stop() {

}

func (s *EnovaServingScaler) RunInWaitGroup(wg *sync.WaitGroup) {
	defer wg.Done()
	s.Run()
}
