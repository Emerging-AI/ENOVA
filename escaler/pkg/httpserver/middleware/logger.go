package middleware

import (
	"bytes"
	"io/ioutil"
	"strings"
	"time"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"

	"github.com/gin-gonic/gin"
)

func RequestResponseLogger() gin.HandlerFunc {
	return func(c *gin.Context) {
		// just for /api/monitor/v1/
		if !strings.Contains(c.Request.URL.Path, "/api/enova/v1") {
			c.Next()
			return
		}

		// 获取请求体
		reqBody, _ := ioutil.ReadAll(c.Request.Body)
		c.Request.Body = ioutil.NopCloser(bytes.NewBuffer(reqBody))

		// 获取响应体
		respWriter := &responseWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
		c.Writer = respWriter

		// 处理请求
		c.Next()

		// 记录请求和响应
		respStr := respWriter.body.String()
		if respStrLen := len(respStr); respStrLen > 1024 {
			respStr = respStr[:1024]
		}

		logger.Info("---------------------------------------------------------")
		logger.Infof("[INFO] [%s] %s %s %s\n%d %s\n",
			time.Now().Format("2006-01-02 15:04:05"),
			c.Request.Method, c.Request.URL.Path, string(reqBody),
			respWriter.status, respStr,
		)
		logger.Info("---------------------------------------------------------")
	}
}

type responseWriter struct {
	body *bytes.Buffer
	gin.ResponseWriter
	status int
}

func (w *responseWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

func (w *responseWriter) WriteHeader(statusCode int) {
	w.status = statusCode
	w.ResponseWriter.WriteHeader(statusCode)
}
