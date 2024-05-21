package main

import (
	"enova/pkg/api"
	"github.com/gin-gonic/gin"
	"net/http"
)

func StartMockEnovaAlgoServer() {
	r := gin.Default()
	r.POST("/api/enovaalgo/v1/config_recommend", func(c *gin.Context) {
		c.JSON(http.StatusOK, api.EnvoaResponse{
			Message: "",
			Code:    0,
			Result: api.ConfigRecommendResult{
				MaxNumSeqs:           32,
				TensorParallelSize:   1,
				GpuMemoryUtilization: 0.8,
				Replicas:             1,
			},
			TraceId: "TraceId",
			Version: "v1",
		})
	})

	r.POST("/api/enovaalgo/v1/anomaly_detect", func(c *gin.Context) {
		c.JSON(http.StatusOK, api.EnvoaResponse{
			Message: "",
			Code:    0,
			Result: api.AnomalyDetectResponse{
				IsAnomaly: 0,
			},
			TraceId: "TraceId",
			Version: "v1",
		})
	})

	r.POST("/api/enovaalgo/v1/anomaly_recover", func(c *gin.Context) {
		c.JSON(http.StatusOK, api.EnvoaResponse{
			Message: "",
			Code:    0,
			Result: api.ConfigRecommendResult{
				MaxNumSeqs:           32,
				TensorParallelSize:   1,
				GpuMemoryUtilization: 0.8,
				Replicas:             1,
			},
			TraceId: "TraceId",
			Version: "v1",
		})
	})
	r.Run(":8181")
}
