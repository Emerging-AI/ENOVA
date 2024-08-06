package api

import (
	"fmt"
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
)

var promClientInitOnce sync.Once

type Metric map[string]string

type ValueSet []interface{}

type Series struct {
	Metric Metric     `json:"metric"`
	Values []ValueSet `json:"values"`
}

type PromData struct {
	ResultType string   `json:"resultType"`
	Result     []Series `json:"result"`
}

type PromResponse struct {
	Status string
	Data   PromData
}

type promClient struct {
	Query      HttpApi[PromResponse]
	QueryRange HttpApi[PromResponse]
}

var PromClient *promClient

func GetPromClient() *promClient {
	promClientInitOnce.Do(func() {
		PromClient = &promClient{
			Query: HttpApi[PromResponse]{
				Method:        "GET",
				Url:           fmt.Sprintf("http://%s:%d/api/v1/query", config.GetEConfig().Detector.Prom.Host, config.GetEConfig().Detector.Prom.Port),
				HeaderBuilder: &EmptyHeaderBuilder{},
			},
			QueryRange: HttpApi[PromResponse]{
				Method:        "GET",
				Url:           fmt.Sprintf("http://%s:%d/api/v1/query_range", config.GetEConfig().Detector.Prom.Host, config.GetEConfig().Detector.Prom.Port),
				HeaderBuilder: &EmptyHeaderBuilder{},
			},
		}
	})
	return PromClient
}
