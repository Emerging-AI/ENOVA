package resource

import (
	"context"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/resource/k8s"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

type K8sResourceClient struct {
	K8sCli *k8s.K8sCli
}

// DeployTask first check whether deployment existed or not
// start task or scale task
func (c *K8sResourceClient) DeployTask(spec meta.TaskSpec) {
	// use deployment to deploy
	workload := k8s.Workload{
		K8sCli: c.K8sCli,
		Spec:   &spec,
	}

	workload.CreateOrUpdate()
}

func (c *K8sResourceClient) DeleteTask(spec meta.TaskSpec) {
	workload := k8s.Workload{
		K8sCli: c.K8sCli,
		Spec:   &spec,
	}
	workload.Delete()
}

func (c *K8sResourceClient) IsTaskRunning(spec meta.TaskSpec) bool {
	workload := k8s.Workload{
		K8sCli: c.K8sCli,
		Spec:   &spec,
	}
	podList, err := workload.GetPodsList()
	if err != nil {
		logger.Errorf("K8sResourceClient IsTaskRunning error: %v", err)
		return false
	}
	if podList.Items[0].Status.Phase == "Running" {
		return true
	}
	return false
}

func (c *K8sResourceClient) GetRuntimeInfos(spec meta.TaskSpec) []meta.RuntimeInfo {
	workload := k8s.Workload{
		K8sCli: c.K8sCli,
		Spec:   &spec,
	}
	podList, err := workload.GetPodsList()
	if err != nil {
		logger.Errorf("GetRuntimeInfos GetPodsList error: %v", err)
		return []meta.RuntimeInfo{}
	}
	if len(podList.Items) == 0 {
		return []meta.RuntimeInfo{}
	}
	ret := make([]meta.RuntimeInfo, len(podList.Items))
	for i, pod := range podList.Items {
		ret[i] = meta.RuntimeInfo{
			ContainerId: pod.Name,
			Name:        pod.Name,
			Status:      string(pod.Status.Phase),
		}
	}
	return ret
}

// SyncStatus sync node relation to
func (c *K8sResourceClient) SyncStatus(spec meta.TaskSpec) {

}

func NewK8sClient() (*kubernetes.Clientset, error) {
	if config.GetEConfig().K8s.InCluster {
		config, err := rest.InClusterConfig()
		if err != nil {
		}
		return kubernetes.NewForConfig(config)
	}
	config, err := clientcmd.BuildConfigFromFlags("", config.GetEConfig().K8s.KubeConfigPath)
	if err != nil {
	}

	return kubernetes.NewForConfig(config)
}

func NewK8sDynamicClient() (*dynamic.DynamicClient, error) {
	if config.GetEConfig().K8s.InCluster {
		config, err := rest.InClusterConfig()
		if err != nil {
		}
		return dynamic.NewForConfig(config)
	}
	config, err := clientcmd.BuildConfigFromFlags("", config.GetEConfig().K8s.KubeConfigPath)
	if err != nil {
	}

	return dynamic.NewForConfig(config)
}

func Newk8sResourcClient() *K8sResourceClient {
	cli, err := NewK8sClient()
	if err != nil {
		panic(err)
	}

	dynamicCli, err := NewK8sDynamicClient()
	if err != nil {
		panic(err)
	}

	return &K8sResourceClient{
		K8sCli: &k8s.K8sCli{
			K8sClient:     cli,
			DynamicClient: dynamicCli,
			Ctx:           context.Background(),
		},
	}
}
