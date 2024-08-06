package api

import (
	"fmt"
	"net/http"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/utils"

	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

// var k8sClientInitOnce sync.Once

type K8sResponse struct {
	Status string
	Data   PromData
}

type k8sHttpApiClient struct {
}

type k8sClient struct {
	Clientset *kubernetes.Clientset
}

type RancherResponse struct {
}

type RancherLoginApi struct {
	*HttpApi[RancherResponse]
}

type RancherLoginResponse struct {
	AccessToken string
}

type RancherHeaderBuilder struct {
	Cache utils.TTLCache
}

func (hb *RancherHeaderBuilder) Build() (map[string]string, error) {
	headers := make(map[string]string)
	token := hb.Cache.Get("rancher_token")
	if token == "" {
		loginResp, err := rancherLogin()
		if err != nil {
			return headers, err
		}
		token = loginResp.AccessToken
	}
	headers["R_SESS"] = token
	return headers, nil
}

func (rapi *RancherLoginApi) Call(Params interface{}, Headers map[string]string) (RancherLoginResponse, error) {
	client := &http.Client{}
	req, err := rapi.GetRequest(Params, Headers)
	if err != nil {
		return RancherLoginResponse{}, err
	}
	res, err := client.Do(req) // todo 处理err
	if err != nil {
		return RancherLoginResponse{}, err
	}

	token := ""
	for _, cookie := range res.Cookies() {
		if cookie.Name == "R_SESS" {
			token = cookie.Value
			break
		}
	}
	return RancherLoginResponse{AccessToken: token}, nil
}

func rancherLogin() (RancherLoginResponse, error) {
	Login := RancherLoginApi{
		&HttpApi[RancherResponse]{
			Method: "POST",
			Url: fmt.Sprintf(
				"http://%s:%d/v3-public/localProviders/local?action=login", config.GetEConfig().K8s.Host, config.GetEConfig().K8s.Port),
		},
	}
	headers := make(map[string]string)
	params := make(map[string]string)
	loginResp, err := Login.Call(params, headers)
	if err != nil {
		logger.Errorf("RancherLoginApi get error: %v", err)
		return RancherLoginResponse{}, err
	}
	return loginResp, nil
}

func NewK8sClient() (k8sClient, error) {
	k8sConfig := &rest.Config{
		// 你可能需要设置其他配置参数
		Host:     "https://<RancherServer>",
		Username: "token-rbvjx",
		Password: "q5r5hk7s2bztcksbtmbzglsb7jckxrgq8ckjf2wdhmv8lt5hqq8d49",
	}
	clientset, err := kubernetes.NewForConfig(k8sConfig)
	if err != nil {
		return k8sClient{}, err
	}
	return k8sClient{
		Clientset: clientset,
	}, nil
}

var K8sHttpApiClient *k8sHttpApiClient

// func GetRancherClient() *k8sHttpApiClient {
// 	k8sClientInitOnce.Do(func() {
// 		headerBuilder := RancherHeaderBuilder{
// 			Cache: utils.NewRedisTTLCache(
// 				config.GetEConfig().Redis.Addr, config.GetEConfig().Redis.Password, config.GetEConfig().Redis.Db),
// 		}
// 		K8sHttpApiClient = &k8sHttpApiClient{}
// 	})
// 	return K8sHttpApiClient
// }
