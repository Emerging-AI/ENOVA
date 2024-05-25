package middleware

import (
	"bytes"
	"encoding/json"
	"net/http"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"

	"github.com/gin-gonic/gin"
)

type EApiResponse struct {
	Message string          `json:"message"`
	Code    int             `json:"code"`
	Result  json.RawMessage `json:"result"`
	TraceId string          `json:"trace_id"`
	Version string          `json:"version"`
}

type responseBodyWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

func (w responseBodyWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

func (w responseBodyWriter) WriteString(s string) (int, error) {
	w.body.WriteString(s)
	return w.ResponseWriter.WriteString(s)
}

func ResponseMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {

		// 调用下一个中间件或路由处理函数
		c.Next()

		// 错误的结果直接返回
		if errResult, ok := c.Get("ErrorResult"); ok {
			c.JSON(http.StatusOK, errResult)
			return
		}

		// 解析成功的返回
		var jsonResult json.RawMessage
		result, ok := c.Get("Data")
		if !ok {
			return
		}

		jsonResult, err := json.Marshal(result)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusInternalServerError, EApiResponse{
				Message: "Internal error",
				Code:    500,
				Result:  jsonResult,
				TraceId: GenerateTraceId(),
				Version: config.GetEConfig().Detector.Api.Version,
			})
			return
		}

		c.JSON(http.StatusOK, EApiResponse{
			Message: "ok",
			Code:    0,
			Result:  jsonResult,
			TraceId: GenerateTraceId(),
			Version: config.GetEConfig().Detector.Api.Version,
		})
	}
}
