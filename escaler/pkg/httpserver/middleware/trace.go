package middleware

import (
	"github.com/gin-gonic/gin"
	uuid "github.com/google/uuid"
)

const TraceIdKey = "trace_id"

func GenerateTraceId() string {
	v4, err := uuid.NewUUID()
	if err != nil {
		panic(err)
	}
	return v4.String()
}

func GetTraceId() gin.HandlerFunc {
	return func(c *gin.Context) {
		traceId := c.GetHeader(TraceIdKey)

		if traceId == "" {
			traceId = GenerateTraceId()
			c.Request.Header.Set(TraceIdKey, traceId)
			c.Set(TraceIdKey, traceId)
		}

		// Set TraceIdKey header
		c.Writer.Header().Set(TraceIdKey, traceId)
	}
}
