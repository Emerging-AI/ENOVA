package main

import (
	"enova/cmd/pilot/docs"
	"enova/internal/detector"
	"enova/internal/scaler"
	"enova/pkg/config"
	"flag"
	"fmt"
	"sync"

	swaggerfiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

func main() {
	confPath := flag.String("conf", "conf/settings.json", "Path to the configuration file")
	flag.Parse()

	fmt.Printf("Using configuration file: %s\n", *confPath)
	econfig := config.GetEConfig()
	econfig.Init(*confPath)
	econfig.PrintConfig()

	docs.SwaggerInfo.Title = "Monitor Service API"
	docs.SwaggerInfo.Description = "This is a monitor service."
	docs.SwaggerInfo.Version = "1.0"
	//docs.SwaggerInfo.Host = "121.36.212.78:30080"
	docs.SwaggerInfo.Host = "0.0.0.0:8183"
	docs.SwaggerInfo.BasePath = "/"
	docs.SwaggerInfo.Schemes = []string{"http", "https"}

	var wg sync.WaitGroup

	d := detector.NewDetectorServer()
	d.GetEngine().GET("/api/pilot/docs/*any", ginSwagger.WrapHandler(swaggerfiles.Handler))

	s := scaler.NewLocalDockerServingScaler()

	wg.Add(2)
	go d.RunInWaitGroup(&wg)
	go s.RunInWaitGroup(&wg)

	wg.Wait()
	fmt.Println("All tasks finished.")
}
