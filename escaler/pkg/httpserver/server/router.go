package server

import "github.com/gin-gonic/gin"

type BaseResource struct {
}

func (r BaseResource) SetResult(c *gin.Context, result interface{}) {
	c.Set("Data", result)
}

func (r BaseResource) SetErrorResult(c *gin.Context, result interface{}) {
	c.Set("ErrorResult", result)
}

type PathResourceInterface interface {
	Path() string
}

type GetResourceInterface interface {
	Get(c *gin.Context)
}

type ListResourceInterface interface {
	List(c *gin.Context)
}

type PostResourceInterface interface {
	Post(c *gin.Context)
}

type PutResourceInterface interface {
	Put(c *gin.Context)
}

type DeleteResourceInterface interface {
	Delete(c *gin.Context)
}
