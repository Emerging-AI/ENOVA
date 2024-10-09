package queue

import (
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
)

type TaskQueue interface {
	Append(meta.TaskSpec)
	Pop() meta.TaskSpec
}

type InnerChanTaskQueue struct {
	Ch   chan meta.TaskSpecInterface
	seen map[meta.TaskSpecInterface]struct{}
	mu   sync.Mutex
}

func (q *InnerChanTaskQueue) Append(task meta.TaskSpecInterface) {
	q.mu.Lock()
	defer q.mu.Unlock()
	if _, exists := q.seen[task]; !exists {
		q.seen[task] = struct{}{}
		q.Ch <- task
	}
}

func (q *InnerChanTaskQueue) Pop() (meta.TaskSpecInterface, bool) {
	task, ok := <-q.Ch
	return task, ok
}
