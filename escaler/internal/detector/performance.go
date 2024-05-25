package detector

import (
	"errors"
	"fmt"
	"strconv"
	"sync"
	"time"

	"github.com/Emerging-AI/ENOVA/escaler/internal/meta"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/api"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
)

func GetLocation() *time.Location {
	location, err := time.LoadLocation("UTC")
	if err != nil {
		logger.Errorf("time.LoadLocation err: %v", err)
	}
	return location
}

type PerformanceDetectorCli struct {
}

type CommonQueryCall func(serviceName string) (api.PromResponse, error)

func (p *PerformanceDetectorCli) CommonMetricQuery(query string, start string, end string, step string) (api.PromResponse, error) {
	var resp api.PromResponse
	params := make(map[string]string)
	headers := make(map[string]string)
	params["query"] = query
	params["start"] = start
	params["end"] = end
	params["step"] = step
	resp, err := api.GetPromClient().QueryRange.Call(params, headers)
	if err != nil {
		logger.Errorf("DetectOnce err: %v", err)
		return resp, err
	}
	return resp, nil
}

func (p *PerformanceDetectorCli) GetPendingRequestMetric(serviceName string) (api.PromResponse, error) {
	location := GetLocation()
	querySql := fmt.Sprintf("avg by(exported_job) (pending_requests{exported_job=~\"%s-replica.*\"})", serviceName)
	return p.CommonMetricQuery(
		querySql,
		time.Now().In(location).Add(-(time.Hour * 3)).Format(time.RFC3339),
		time.Now().In(location).Format(time.RFC3339),
		"60s")
}

func (p *PerformanceDetectorCli) GetActiveRequestMetric(serviceName string) (api.PromResponse, error) {
	location := GetLocation()
	querySql := fmt.Sprintf("avg by(exported_job) (http_server_active_requests{exported_job=~\"%s-replica.*\"})", serviceName)
	return p.CommonMetricQuery(
		querySql,
		time.Now().In(location).Add(-(time.Hour * 3)).Format(time.RFC3339),
		time.Now().In(location).Format(time.RFC3339),
		"60s")
}

func (p *PerformanceDetectorCli) GetRunningRequestMetric(serviceName string) (api.PromResponse, error) {
	location := GetLocation()
	querySql := fmt.Sprintf("avg by(exported_job) (running_requests{exported_job=~\"%s-replica.*\"})", serviceName)
	return p.CommonMetricQuery(
		querySql,
		time.Now().In(location).Add(-(time.Hour * 3)).Format(time.RFC3339),
		time.Now().In(location).Format(time.RFC3339),
		"60s")
}

func (p *PerformanceDetectorCli) GetGpuKVCacheUsageMetric(serviceName string) (api.PromResponse, error) {
	location := GetLocation()
	querySql := fmt.Sprintf("avg by(exported_job) (gpu_kv_cache_usage_percent{exported_job=~\"%s-replica.*\"})", serviceName)
	return p.CommonMetricQuery(
		querySql,
		time.Now().In(location).Add(-(time.Hour * 3)).Format(time.RFC3339),
		time.Now().In(location).Format(time.RFC3339),
		"1m")
}

func (p *PerformanceDetectorCli) GetServerNewRequestsMetric(serviceName string) (api.PromResponse, error) {
	location := GetLocation()
	querySql := fmt.Sprintf("sum(rate(http_server_requests_total{exported_job=~\"%s-replica.*\"}[1m]) * 60) by (exported_job)", serviceName)
	return p.CommonMetricQuery(
		querySql,
		time.Now().In(location).Add(-(time.Hour * 3)).Format(time.RFC3339),
		time.Now().In(location).Format(time.RFC3339),
		"1m")
}

func (p *PerformanceDetectorCli) GetServerSuccessRequestsMetric(serviceName string) (api.PromResponse, error) {
	location := GetLocation()
	querySql := fmt.Sprintf("avg by(service) (increase(traces_spanmetrics_calls_total{service=~\"%s-replica.*\", span_name=\"POST /generate\", http_status_code=~\"2..\"}[1m]))", serviceName)
	return p.CommonMetricQuery(
		querySql,
		time.Now().In(location).Add(-(time.Hour * 3)).Format(time.RFC3339),
		time.Now().In(location).Format(time.RFC3339),
		"1m")
}

func (p *PerformanceDetectorCli) GetThroughputTokensMetric() {
	params := make(map[string]string)
	headers := make(map[string]string)
	location := GetLocation()
	params["query"] = "avg by(exported_job) (avg_prompt_throughput_tokens_per_second)"
	params["start"] = time.Now().In(location).Add(-(time.Minute * 30)).Format(time.RFC3339)
	params["end"] = time.Now().In(location).Format(time.RFC3339)
	params["step"] = "1m"
	_, err := api.GetPromClient().QueryRange.Call(params, headers)
	if err != nil {
		logger.Errorf("DetectOnce err: %v", err)
		return
	}
}

func BuildMetricSeriesByPromResponse(series api.Series) []api.MetricValue {
	result := []api.MetricValue{}
	for _, value := range series.Values {
		// 将时间戳和值转换为整数
		timestamp, ok := value[0].(float64)
		if !ok {
			fmt.Println("Error converting timestamp")
			continue
		}
		val, err := strconv.ParseFloat(value[1].(string), 64)
		if err != nil {
			fmt.Println("Error converting value:", err)
			continue
		}
		// 添加到结果切片中
		result = append(result, api.MetricValue{float64(timestamp), float64(val)})
	}
	return result
}

func (p *PerformanceDetectorCli) AsyncQuery(
	resultCache map[string]map[string][]api.MetricValue, wg *sync.WaitGroup, resultLock *sync.Mutex, queryCall CommonQueryCall, serviceName, resultKey string) {
	defer wg.Done()
	resp, err := queryCall(serviceName)
	if err != nil {
		logger.Errorf("AsyncQuery queryCall: %v, error: %v", queryCall, err)
		return
	}
	for _, series := range resp.Data.Result {
		var containerName string
		var metricValuesMap map[string][]api.MetricValue
		ok := false
		for _, containerName = range series.Metric {
			resultLock.Lock()
			metricValuesMap, ok = resultCache[containerName]
			if !ok {
				metricValuesMap = make(map[string][]api.MetricValue)
				resultCache[containerName] = metricValuesMap
			}
			resultLock.Unlock()
		}
		resultLock.Lock()
		metricValuesMap[resultKey] = BuildMetricSeriesByPromResponse(series)
		resultLock.Unlock()
	}
}

func (p *PerformanceDetectorCli) GetVllmCurrentMetricParams(spec meta.TaskSpecInterface) (api.AnomalyRecoverRequest, error) {
	var resp api.AnomalyRecoverRequest
	result := make(map[string]map[string][]api.MetricValue)
	backendConfig, ok := spec.GetBackendConfig().(*meta.VllmBackendConfig)
	if !ok {
		return resp, errors.New("GetVllmCurrentMetricParams get wrong spec input")
	}

	var wg sync.WaitGroup
	wg.Add(6)

	var resultLock sync.Mutex
	go p.AsyncQuery(result, &wg, &resultLock, p.GetPendingRequestMetric, spec.GetExporterServiceName(), "PendingRequests")
	go p.AsyncQuery(result, &wg, &resultLock, p.GetActiveRequestMetric, spec.GetExporterServiceName(), "ActiveRequests")
	go p.AsyncQuery(result, &wg, &resultLock, p.GetRunningRequestMetric, spec.GetExporterServiceName(), "RunningRequests")
	go p.AsyncQuery(result, &wg, &resultLock, p.GetGpuKVCacheUsageMetric, spec.GetExporterServiceName(), "GpuKVCacheUsage")
	go p.AsyncQuery(result, &wg, &resultLock, p.GetServerNewRequestsMetric, spec.GetExporterServiceName(), "ServerNewRequests")
	go p.AsyncQuery(result, &wg, &resultLock, p.GetServerSuccessRequestsMetric, spec.GetExporterServiceName(), "ServerSuccessRequests")

	wg.Wait()

	metricValues := []api.Metrics{}
	for _, singleMetricValues := range result {

		metricValues = append(metricValues, api.Metrics{
			ActiveRequests:        RobustGetMetricValues(singleMetricValues, "ActiveRequests"),
			PendingRequests:       RobustGetMetricValues(singleMetricValues, "PendingRequests"),
			RunningRequests:       RobustGetMetricValues(singleMetricValues, "RunningRequests"),
			GPUKVCacheUsage:       RobustGetMetricValues(singleMetricValues, "GpuKVCacheUsage"),
			ServerNewRequests:     RobustGetMetricValues(singleMetricValues, "ServerNewRequests"),
			ServerSuccessRequests: RobustGetMetricValues(singleMetricValues, "ServerSuccessRequests"),
		})
	}

	resp = api.AnomalyRecoverRequest{
		Metrics: metricValues,
		Configurations: api.Configurations{
			MaxNumSeqs:           backendConfig.MaxNumSeqs,
			TensorParallelSize:   backendConfig.TensorParallelSize,
			GPUMemoryUtilization: backendConfig.GpuMemoryUtilization,
			Replicas:             spec.GetReplica(),
		},
		Llm: spec.GetModelConfig().Llm,
		Gpu: spec.GetModelConfig().Gpu,
	}
	return resp, nil
}

func RobustGetMetricValues(singleMetricValues map[string][]api.MetricValue, metricName string) []api.MetricValue {
	values, ok := singleMetricValues[metricName]
	if !ok {
		values = []api.MetricValue{}
	}
	return values
}
