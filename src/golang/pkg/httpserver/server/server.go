package server

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"enova/pkg/config"

	"enova/pkg/logger"

	"enova/pkg/httpserver/middleware"

	"enova/pkg/httpserver/utils"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"golang.org/x/sync/errgroup"
)

// type GenericAPIServer gin.Engine.
type APIServer struct {
	Middlewares []gin.HandlerFunc
	Resources   []interface{}
	// ShutdownTimeout is the timeout used for server shutdown. This specifies the timeout before server
	// gracefully shutdown returns.
	ShutdownTimeout time.Duration

	engine          *gin.Engine
	healthz         bool
	enableMetrics   bool
	enableProfiling bool
	// wrapper for gin.Engine
	server *http.Server
}

func (s *APIServer) InitAPIServer() {
	s.engine = gin.Default()
	s.InstallMiddlewares()
	s.InstallResources()
	s.InstallAPIs()
}

func (s *APIServer) GetEngine() *gin.Engine {
	return s.engine
}

func (s *APIServer) InstallResources() {
	apiPrefix := fmt.Sprintf("/api%s/%s", config.GetEConfig().Detector.Api.UrlPrefix, config.GetEConfig().Detector.Api.Version)
	appGroup := s.engine.Group(apiPrefix)
	for _, resource := range s.Resources {
		var path = ""
		if utils.HasMethod(resource, "Path") {
			path = resource.(PathResourceInterface).Path()
		} else {
			panic(errors.New(fmt.Sprintf("resouce %v Path function is not implemented", resource)))
		}
		if utils.HasMethod(resource, "Get") {
			appGroup.GET(path, resource.(GetResourceInterface).Get)
		}
		if utils.HasMethod(resource, "Post") {
			appGroup.POST(path, resource.(PostResourceInterface).Post)
		}
		if utils.HasMethod(resource, "Put") {
			appGroup.PUT(path, resource.(PutResourceInterface).Put)
		}
		if utils.HasMethod(resource, "Delete") {
			appGroup.DELETE(path, resource.(DeleteResourceInterface).Delete)
		}
	}
}

// InstallAPIs install generic apis.
func (s *APIServer) InstallAPIs() {

}

// InstallMiddlewares install generic middlewares.
func (s *APIServer) InstallMiddlewares() {
	// necessary middlewares
	s.engine.Use(middleware.GetTraceId())
	s.engine.Use(middleware.RequestResponseLogger())
	s.engine.Use(middleware.ResponseMiddleware())

	// cors
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true

	s.engine.Use(cors.New(config))

	// install custom middlewares
	for _, m := range s.Middlewares {
		logger.Info("install middleware: %s", m)
		s.engine.Use(m)
	}
}

// Run spawns the http server. It only returns when the port cannot be listened on initially.
func (s *APIServer) Run() error {
	c := config.GetEConfig()
	addr := c.Detector.Api.GetAddr()
	s.server = &http.Server{
		Addr:    addr,
		Handler: s.engine,
		// ReadTimeout:    10 * time.Second,
		// WriteTimeout:   10 * time.Second,
		// MaxHeaderBytes: 1 << 20,
	}

	var eg errgroup.Group

	// Initializing the server in a goroutine so that
	// it won't block the graceful shutdown handling below
	eg.Go(func() error {
		logger.Info("Start to listening the incoming requests on http address: %s", addr)

		if err := s.server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Fatal(err.Error())

			return err
		}

		logger.Info("Server on %s stopped", addr)

		return nil
	})

	// Ping the server to make sure the router is working.
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if s.healthz {
		if err := s.ping(ctx); err != nil {
			return err
		}
	}

	if err := eg.Wait(); err != nil {
		log.Fatal(err.Error())
	}

	return nil
}

// Close graceful shutdown the api server.
func (s *APIServer) Close() {
	// The context is used to inform the server it has 10 seconds to finish
	// the request it is currently handling
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := s.server.Shutdown(ctx); err != nil {
		logger.Warn("Shutdown secure server failed: %s", err.Error())
	}

	if err := s.server.Shutdown(ctx); err != nil {
		logger.Warn("Shutdown insecure server failed: %s", err.Error())
	}
}

// ping pings the http server to make sure the router is working.
func (s *APIServer) ping(ctx context.Context) error {
	addr := config.GetEConfig().Detector.Api.GetAddr()
	url := fmt.Sprintf("http://%s/healthz", addr)
	if strings.Contains(addr, "0.0.0.0") {
		url = fmt.Sprintf("http://127.0.0.1:%s/healthz", strings.Split(addr, ":")[1])
	}

	for {
		// Change NewRequest to NewRequestWithContext and pass context it
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			return err
		}
		// Ping the server by sending a GET request to `/healthz`.

		resp, err := http.DefaultClient.Do(req)
		if err == nil && resp.StatusCode == http.StatusOK {
			logger.Info("The router has been deployed successfully.")

			resp.Body.Close()
			return nil
		}

		// Sleep for a second to continue the next ping.
		logger.Info("Waiting for the router, retry in 1 second.")
		time.Sleep(1 * time.Second)

		select {
		case <-ctx.Done():
			log.Fatal("can not ping http server within the specified time interval.")
		default:
		}
	}
}
