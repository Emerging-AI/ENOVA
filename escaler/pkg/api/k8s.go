package api

import "sync"

var k8sClientInitOnce sync.Once

type K8sResponse struct {
	Status string
	Data   PromData
}

type K8sHttpApi struct {
	*HttpApi
}
