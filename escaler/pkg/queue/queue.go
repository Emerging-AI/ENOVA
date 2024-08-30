package queue

import "github.com/Emerging-AI/ENOVA/escaler/pkg/meta"

type TaskQueue interface {
	Append(meta.TaskSpec)
	Pop() meta.TaskSpec
}

type InnerChanTaskQueue struct {
	Ch chan meta.TaskSpecInterface
}

func (q *InnerChanTaskQueue) Append(task meta.TaskSpecInterface) {
	q.Ch <- task
}

func (q *InnerChanTaskQueue) Pop() (meta.TaskSpecInterface, bool) {
	task, ok := <-q.Ch
	return task, ok
}
