package config

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strconv"
	"strings"
	"sync"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/utils"
)

var once sync.Once

type TritonInferConfig struct {
	Host      string
	Port      int
	ModelName string
}

type EnovaInferConfig struct {
	ExecutionControl          TritonInferConfig
	PerformanceDetection      TritonInferConfig
	ApplicationDomainAdaption TritonInferConfig
}

func (e TritonInferConfig) GetUrl() string {
	return fmt.Sprintf("http://%s:%d/", e.Host, e.Port)
}

type DockerConfig struct {
}

type ScalerConfig struct {
}

type PromConfig struct {
	Host string
	Port int
}

type ApiConfig struct {
	Host      string
	Port      int
	Version   string
	UrlPrefix string `json:"url_prefix"`
}

func (api ApiConfig) GetAddr() string {
	return fmt.Sprintf("%s:%d", api.Host, api.Port)
}

type DetectorConfig struct {
	Prom           PromConfig `json:"prom"`
	Api            ApiConfig  `json:"api"`
	DetectInterval int64      `json:"detect_interval"`
}

type LoggerConfig struct {
	Level string
	Name  string
	Path  string
}

type ZmqConfig struct {
	Host string
	Port int
}

type ServingConfig struct {
	Image        string   `json:"image"`
	StartCmd     []string `json:"start_cmd"`
	Network      string   `json:"network"`
	NetworkAlias string   `json:"network_alias"`
	Name         string   `json:"name"`
}

type EnovaAlgoConfig struct {
	Host string
}

type RedisConfig struct {
	Addr     string
	Password string
	Db       int
}

type ResourceBackendType string

const (
	ResourceBackendTypeDocker = "docker"
	ResourceBackendTypeK8s    = "k8s"
)

type ResourceBackendConfig struct {
	Type ResourceBackendType
}

type EConfig struct {
	Docker          DockerConfig
	Detector        DetectorConfig
	Scaler          ScalerConfig
	Zmq             ZmqConfig
	Redis           RedisConfig
	Logger          LoggerConfig
	K8s             K8sConfig
	Serving         ServingConfig         `json:"serving"`
	EnovaAlgo       EnovaAlgoConfig       `json:"enova_algo"`
	ResourceBackend ResourceBackendConfig `json:"resource_backend"`
}

type K8sConfig struct {
	InCluster      bool   `json:"in_cluster"`
	KubeConfigPath string `json:"kube_config_path"`
}

func (c *EConfig) Init(configPath string) error {
	bytes, err := os.ReadFile(configPath)
	if err != nil {
		return err
	}

	err = json.Unmarshal(bytes, c)
	if err != nil {
		return err
	}

	// environment first
	enovaZmqConfig, ok := os.LookupEnv("ENOVA_ZMQ_CONFIG")
	if ok {
		err = json.Unmarshal([]byte(enovaZmqConfig), &c.Zmq)
		if err != nil {
			return err
		}
	}
	enovaDockerConfig, ok := os.LookupEnv("ENOVA_DOCKER_CONFIG")
	if ok {
		if err = json.Unmarshal([]byte(enovaDockerConfig), &c.Docker); err != nil {
			return err
		}
	}
	enovaLoggerConfig, ok := os.LookupEnv("ENOVA_LOGGER_CONFIG")
	if ok {
		err := json.Unmarshal([]byte(enovaLoggerConfig), &c.Logger)
		if err != nil {
			return err
		}
	}
	enovaDectorConfig, ok := os.LookupEnv("ENOVA_DETECTOR_CONFIG")
	if ok {
		err := json.Unmarshal([]byte(enovaDectorConfig), &c.Detector)
		if err != nil {
			return err
		}
	}
	enovaScalerConfig, ok := os.LookupEnv("ENOVA_SCALER_CONFIG")
	if ok {
		err := json.Unmarshal([]byte(enovaScalerConfig), &c.Scaler)
		if err != nil {
			return err
		}
	}

	allFields := utils.GetAllField(c.Serving)
	v := reflect.ValueOf(&c.Serving).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_ENODE")

	allFields = utils.GetAllField(c.Logger)
	v = reflect.ValueOf(&c.Logger).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_LOGGER")

	allFields = utils.GetAllField(c.Detector)
	v = reflect.ValueOf(&c.Detector).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_DETECTOR")

	allFields = utils.GetAllField(c.Detector.Api)
	v = reflect.ValueOf(&c.Detector.Api).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_DETECTOR_API")

	allFields = utils.GetAllField(c.Docker)
	v = reflect.ValueOf(&c.Docker).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_DOCKER")

	allFields = utils.GetAllField(c.EnovaAlgo)
	v = reflect.ValueOf(&c.EnovaAlgo).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_ENOVAALGO")

	allFields = utils.GetAllField(c.Scaler)
	v = reflect.ValueOf(&c.Scaler).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_SCALAR")

	allFields = utils.GetAllField(c.Redis)
	v = reflect.ValueOf(&c.Redis).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_REDIS")

	allFields = utils.GetAllField(c.Zmq)
	v = reflect.ValueOf(&c.Zmq).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_ZMQ")

	allFields = utils.GetAllField(c.K8s)
	v = reflect.ValueOf(&c.K8s).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_K8S")

	allFields = utils.GetAllField(c.ResourceBackend)
	v = reflect.ValueOf(&c.ResourceBackend).Elem()
	c.DynamicUpdateConfig(&v, allFields, "ENOVA_RESOURCE_BACKEND")
	return nil
}

func (c *EConfig) DynamicUpdateConfig(reflectValue *reflect.Value, allFields []reflect.StructField, envPrefix string) {
	for _, f := range allFields {
		envName := fmt.Sprintf("%s_%s", envPrefix, strings.ToUpper(f.Name))
		envValue, ok := os.LookupEnv(envName)
		if !ok {
			continue
		}
		switch f.Type.Kind() {
		case reflect.String:
			reflectValue.FieldByName(f.Name).SetString(envValue)
		case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
			intVal, err := strconv.ParseInt(envValue, 10, 64)
			if err != nil {
				fmt.Printf("cannot convert %s to int for field %s", envValue, f.Name)
			}
			reflectValue.FieldByName(f.Name).SetInt(intVal)
		case reflect.Bool:
			boolVal, err := strconv.ParseBool(envValue)
			if err != nil {
				fmt.Printf("cannot convert %s to bool for field %s", envValue, f.Name)
			}
			reflectValue.FieldByName(f.Name).SetBool(boolVal)
		}
	}
}

func (c *EConfig) PrintConfig() {
	bodyBytes, err := json.MarshalIndent(c, "", "\t")
	if err != nil {
		fmt.Printf("PrintConfig err: %v\n", err)
		return
	}
	fmt.Printf("config: %s\n", string(bodyBytes))
}

var instance *EConfig

func GetEConfig() *EConfig {
	once.Do(func() {
		instance = &EConfig{}
		// default init
		var configPath = "conf/settings.json"
		err := instance.Init(configPath)
		if err != nil {
			fmt.Println("Loading config err:", err)
		}
	})
	return instance
}
