package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
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

type PromHttpApi struct {
	HttpApi
}

func (papi *PromHttpApi) Call(Params interface{}, Headers map[string]string) (PromResponse, error) {
	client := &http.Client{}
	req, err := papi.GetRequest(Params, Headers)
	if err != nil {
		return PromResponse{}, err
	}
	res, err := client.Do(req) // todo 处理err
	if err != nil {
		return PromResponse{}, err
	}
	return papi.processResponse(res)
}

func (papi *PromHttpApi) processResponse(httpresp *http.Response) (PromResponse, error) {
	defer httpresp.Body.Close()
	var resp PromResponse
	if httpresp.StatusCode != http.StatusOK {
		resBody, _ := io.ReadAll(httpresp.Body)
		msg := fmt.Sprintf("PromHttpApi get StatusOK not ok: status code: %d, res: %s", httpresp.StatusCode, resBody)
		logger.Infof(msg)
		return resp, errors.New(msg)
	}
	resBody, _ := io.ReadAll(httpresp.Body)
	if err := json.Unmarshal(resBody, &resp); err != nil {
		logger.Error("Error parsing JSON response: %v", err)
		return resp, err
	}
	return resp, nil
}

type promClient struct {
	Query      PromHttpApi
	QueryRange PromHttpApi
}

var PromClient *promClient

func GetPromClient() *promClient {
	promClientInitOnce.Do(func() {
		PromClient = &promClient{
			Query: PromHttpApi{
				HttpApi{
					Method: "GET",
					Url:    fmt.Sprintf("http://%s:%d/api/v1/query", config.GetEConfig().Detector.Prom.Host, config.GetEConfig().Detector.Prom.Port),
				},
			},
			QueryRange: PromHttpApi{
				HttpApi{
					Method: "GET",
					Url:    fmt.Sprintf("http://%s:%d/api/v1/query_range", config.GetEConfig().Detector.Prom.Host, config.GetEConfig().Detector.Prom.Port),
				},
			},
		}
	})
	return PromClient
}
