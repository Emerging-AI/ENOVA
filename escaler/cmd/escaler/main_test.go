package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/detector"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/scaler"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/api"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestPilot(t *testing.T) {
	// start mock enova algo server
	go StartMockEnovaAlgoServer()
	config.GetEConfig().Init("../../enova/template/deployment/docker-compose/escaler/conf/settings.json")
	config.GetEConfig().PrintConfig()
	gin.SetMode(gin.TestMode)
	var wg sync.WaitGroup

	performaceCli := detector.PerformanceDetectorCli{}

	d := detector.NewDetectorServer()
	s := scaler.NewLocalDockerServingScaler()

	wg.Add(2)
	go d.RunInWaitGroup(&wg)
	go s.RunInWaitGroup(&wg)

	time.Sleep(3 * time.Second)
	envs := []meta.Env{
		meta.Env{
			Name:  "http_proxy",
			Value: "http://192.168.3.2:7892",
		},
		meta.Env{
			Name:  "https_proxy",
			Value: "http://192.168.3.2:7892",
		},
	}

	volumnes := []meta.Volume{
		meta.Volume{
			MountPath: "/root/.cache",
			HostPath:  "/root/.cache",
		},
	}

	extraConfig := make(map[string]string)
	extraConfig["test"] = "test1"
	extraConfig["test2"] = "test2"
	taskName := "test-enode"
	testTask := meta.TaskSpec{
		Name:                taskName,
		Model:               "THUDM/chatglm3-6b",
		Host:                "0.0.0.0",
		Port:                9199,
		Backend:             "vllm",
		ExporterEndpoint:    "192.168.3.2:32893",
		ExporterServiceName: "enova-chatglm-5oQa",
		ModelConfig: meta.ModelConfig{
			Llm: api.Llm{
				Framework: "chatglm",
				Param:     6,
			},
			Gpu: api.Gpu{
				Name: "4090",
				Spec: 24,
				Num:  1,
			},
			Version: "test",
		},
		BackendConfig: &meta.VllmBackendConfig{
			// MaxNumSeqs:           1,
			// TensorParallelSize:   1,
			// GpuMemoryUtilization: 0.5,
			VllmMode:        "normal",
			TrustRemoteCode: true,
		},
		Replica:            1,
		Envs:               envs,
		Volumes:            volumnes,
		BackendExtraConfig: extraConfig,
	}

	pResult, err := performaceCli.GetVllmCurrentMetricParams(&testTask)

	if err != nil {

	}
	bytesData, _ := json.Marshal(pResult)
	fmt.Printf("pResult: %s\n", string(bytesData))

	bodyBytes, _ := json.Marshal(testTask)
	req, _ := http.NewRequest("POST", "/api/escaler/v1/docker/deploy", bytes.NewBuffer(bodyBytes))
	w := httptest.NewRecorder()
	d.GetEngine().ServeHTTP(w, req)

	var resp api.EnvoaResponse
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		logger.Errorf("parse Result Error %v", err)
	}
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "Success", resp.Result.(string))
	time.Sleep(1 * time.Second)

	// query task
	req, _ = http.NewRequest("GET", fmt.Sprintf("/api/escaler/v1/docker/deploy?task_name=%s", taskName), nil)
	w = httptest.NewRecorder()
	d.GetEngine().ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	var getResp api.EnvoaResponse
	if err := json.Unmarshal(w.Body.Bytes(), &getResp); err != nil {
		logger.Errorf("parse Result Error %v", err)
	}
	_, ok := getResp.Result.(map[string]interface{})
	assert.Equal(t, ok, true)

	// query task detect history
	time.Sleep(10 * time.Second)
	req, _ = http.NewRequest("GET", fmt.Sprintf("/api/escaler/v1/task/detect/history?task_name=%s", taskName), nil)
	w = httptest.NewRecorder()
	d.GetEngine().ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		logger.Errorf("parse Result Error %v", err)
	}
	_, ok = resp.Result.(map[string]interface{})
	assert.Equal(t, ok, true)

	// delete task
	time.Sleep(30 * time.Second)
	req, _ = http.NewRequest("DELETE", fmt.Sprintf("/api/escaler/v1/docker/deploy?task_name=%s", taskName), nil)
	w = httptest.NewRecorder()
	d.GetEngine().ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		logger.Errorf("parse Result Error %v", err)
	}
	assert.Equal(t, "Success", resp.Result.(string))

	wg.Wait()

	fmt.Println("All tasks finished.")
}
