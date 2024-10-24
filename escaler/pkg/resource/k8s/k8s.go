package k8s

import (
	"context"
	"fmt"

	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
	rscutils "github.com/Emerging-AI/ENOVA/escaler/pkg/resource/utils"
	k8sresource "k8s.io/apimachinery/pkg/api/resource"

	v1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/intstr"

	"github.com/mitchellh/mapstructure"
	otalv1 "github.com/open-telemetry/opentelemetry-operator/apis/v1beta1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
)

var collectorServiceAccount = "otel-collector"

type K8sCli struct {
	K8sClient     *kubernetes.Clientset
	DynamicClient *dynamic.DynamicClient
	Ctx           context.Context
}

type Workload struct {
	K8sCli *K8sCli
	Spec   *meta.TaskSpec
}

func (w *Workload) CreateOrUpdate() {
	podList, err := w.GetPodsList()
	if err != nil {
		logger.Errorf("K8sResourceClient DeployTask check GetPodsList get error: %v", err)
		return
	}
	if len(podList.Items) == 0 {
		logger.Debug("workload.GetPodsList get empty podlist")
		_, err := w.CreateWorkload()
		if err != nil {
			return
		}
	} else {
		logger.Debug("workload.GetPodsList get podlist")
		_, err := w.UpdateWorkload()
		if err != nil {
			return
		}
	}

	_, err = w.GetService()
	if err != nil {
		logger.Debugf("K8sResourceClient DeployTask check service get error: %v", err)
		_, err = w.CreateService()
		if err != nil {
			return
		}
	} else {
		_, err = w.UpdateService()
		if err != nil {
			return
		}
	}

	_, err = w.GetIngress()
	if err != nil {
		logger.Debugf("K8sResourceClient DeployTask check ingress get error: %v", err)
		_, err = w.CreateIngress()
		if err != nil {
			return
		}
	} else {
		_, err = w.UpdateIngress()
		if err != nil {
			return
		}
	}

	if w.Spec.Collector.Enable {
		_, err = w.GetCollector()
		if err != nil {
			_, err = w.CreateCollector()
			if err != nil {
				return
			}
		} else {
			_, err = w.UpdateCollector()
			if err != nil {
				return
			}
		}
	}
}

// Create 1. create workload, 2. create ingress 3. create service
func (w *Workload) Create() {
	_, err := w.CreateWorkload()
	if err != nil {
		return
	}
	_, err = w.CreateService()
	if err != nil {
		return
	}
	_, err = w.CreateIngress()
	if err != nil {
		return
	}
}

func (w *Workload) Update() {
	_, err := w.UpdateWorkload()
	if err != nil {
		return
	}
	_, err = w.UpdateService()
	if err != nil {
		return
	}
	_, err = w.UpdateIngress()
	if err != nil {
		return
	}
}

func (w *Workload) Delete() {
	w.DeleteWorkload()
	w.DeleteService()
	w.DeleteIngress()
	w.DeleteCollector()
}

func (w *Workload) CreateWorkload() (*v1.Deployment, error) {
	deployment := w.buildDeployment()
	opts := metav1.CreateOptions{}
	ret, err := w.K8sCli.K8sClient.AppsV1().Deployments(w.Spec.Namespace).Create(w.K8sCli.Ctx, &deployment, opts)
	if err != nil {
		logger.Errorf("Workload CreateWorkload error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) UpdateWorkload() (*v1.Deployment, error) {
	deployment := w.buildDeployment()
	opts := metav1.UpdateOptions{}
	ret, err := w.K8sCli.K8sClient.AppsV1().Deployments(w.Spec.Namespace).Update(w.K8sCli.Ctx, &deployment, opts)
	if err != nil {
		logger.Errorf("Workload UpdateWorkload error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) DeleteWorkload() error {
	if err := w.K8sCli.K8sClient.AppsV1().Deployments(w.Spec.Namespace).Delete(w.K8sCli.Ctx, w.Spec.Name, metav1.DeleteOptions{}); client.IgnoreNotFound(err) != nil {
		logger.Errorf("Workload DeleteWorkload error: %v", err)
		return err
	}
	return nil
}

func (w *Workload) CreateIngress() (*networkingv1.Ingress, error) {
	opts := metav1.CreateOptions{}
	ingress := w.buildIngress()
	ret, err := w.K8sCli.K8sClient.NetworkingV1().Ingresses(w.Spec.Namespace).Create(w.K8sCli.Ctx, &ingress, opts)
	if err != nil {
		logger.Errorf("Workload CreateIngress error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) CreateService() (*corev1.Service, error) {
	opts := metav1.CreateOptions{}
	service := w.buildService()
	ret, err := w.K8sCli.K8sClient.CoreV1().Services(w.Spec.Namespace).Create(w.K8sCli.Ctx, &service, opts)
	if err != nil {
		logger.Errorf("Workload CreateService error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) UpdateIngress() (*networkingv1.Ingress, error) {
	opts := metav1.UpdateOptions{}
	ingress := w.buildIngress()
	ret, err := w.K8sCli.K8sClient.NetworkingV1().Ingresses(w.Spec.Namespace).Update(w.K8sCli.Ctx, &ingress, opts)
	if err != nil {
		logger.Errorf("Workload UpdateIngress error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) UpdateService() (*corev1.Service, error) {
	opts := metav1.UpdateOptions{}
	service := w.buildService()
	ret, err := w.K8sCli.K8sClient.CoreV1().Services(w.Spec.Namespace).Update(w.K8sCli.Ctx, &service, opts)
	if err != nil {
		logger.Errorf("Workload UpdateService error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) DeleteIngress() error {
	if err := w.K8sCli.K8sClient.NetworkingV1().Ingresses(w.Spec.Namespace).Delete(w.K8sCli.Ctx, w.buildIngress().Name, metav1.DeleteOptions{}); client.IgnoreNotFound(err) != nil {
		logger.Errorf("Workload DeleteIngress error: %v", err)
		return err
	}
	return nil
}

func (w *Workload) DeleteService() error {
	if err := w.K8sCli.K8sClient.CoreV1().Services(w.Spec.Namespace).Delete(w.K8sCli.Ctx, w.buildService().Name, metav1.DeleteOptions{}); client.IgnoreNotFound(err) != nil {
		logger.Errorf("Workload DeleteService error: %v", err)
		return err
	}
	return nil
}

func (w *Workload) buildDeployment() v1.Deployment {
	replicas := int32(w.Spec.Replica)
	matchLabels := make(map[string]string)
	matchLabels["enovaserving-name"] = w.Spec.Name
	cmd := rscutils.BuildCmdFromTaskSpec(*w.Spec)

	env := make([]corev1.EnvVar, len(w.Spec.Envs))
	for i, e := range w.Spec.Envs {
		env[i] = corev1.EnvVar{
			Name:  e.Name,
			Value: e.Value,
		}
	}

	livenessProbe := corev1.Probe{}
	readinessProbe := corev1.Probe{}
	probe := corev1.Probe{ProbeHandler: corev1.ProbeHandler{HTTPGet: &corev1.HTTPGetAction{Path: "/metrics",
		Port: intstr.IntOrString{IntVal: int32(w.Spec.Port)}}}, InitialDelaySeconds: 30}
	if w.Spec.Backend == "vllm" {
		livenessProbe = probe
		livenessProbe.FailureThreshold = 600
		readinessProbe = probe
	}

	// default mount ~/.cache to host data disk
	deployment := v1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      w.Spec.Name,
			Namespace: w.Spec.Namespace,
			Labels:    matchLabels,
		},
		Spec: v1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: matchLabels,
			},
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Image:           w.Spec.Image,
							ImagePullPolicy: corev1.PullAlways,
							Name:            w.Spec.Name,
							Command:         cmd[:1],
							Args:            cmd[1:],
							LivenessProbe:   &livenessProbe,
							ReadinessProbe:  &readinessProbe,
							Ports: []corev1.ContainerPort{
								{
									ContainerPort: int32(w.Spec.Port),
									Protocol:      corev1.ProtocolTCP,
								},
							},
							Env: env,
						},
					},
				},
			},
		},
	}
	volumes := make([]corev1.Volume, len(w.Spec.Volumes))
	volumeMounts := make([]corev1.VolumeMount, len(w.Spec.Volumes))
	if len(w.Spec.Volumes) > 0 {
		for i, v := range w.Spec.Volumes {
			volumes[i] = corev1.Volume{
				VolumeSource: corev1.VolumeSource{
					HostPath: &corev1.HostPathVolumeSource{
						Path: v.HostPath,
					},
				},
				Name: fmt.Sprintf("hostpath%d", i),
			}
			volumeMounts[i] = corev1.VolumeMount{
				Name:      fmt.Sprintf("hostpath%d", i),
				MountPath: v.MountPath,
			}
		}
	}
	// if will add shm by default
	shmLimitSize := k8sresource.MustParse("1Gi")
	volumes = append(volumes, corev1.Volume{
		VolumeSource: corev1.VolumeSource{
			EmptyDir: &corev1.EmptyDirVolumeSource{
				Medium:    corev1.StorageMediumMemory,
				SizeLimit: &shmLimitSize,
			},
		},
		Name: "shm",
	})
	volumeMounts = append(volumeMounts, corev1.VolumeMount{
		Name:      "shm",
		MountPath: "/dev/shm",
	})
	deployment.Spec.Template.Spec.Volumes = volumes
	deployment.Spec.Template.Spec.Containers[0].VolumeMounts = volumeMounts
	if len(w.Spec.NodeSelector) > 0 {
		deployment.Spec.Template.Spec.NodeSelector = w.Spec.NodeSelector
	}

	request := corev1.ResourceList{
		corev1.ResourceName("nvidia.com/gpu"): k8sresource.MustParse(w.Spec.Resources.GPU),
	}
	deployment.Spec.Template.Spec.Containers[0].Resources = corev1.ResourceRequirements{
		Limits:   request,
		Requests: request,
	}
	deployment.Spec.Template.Labels = matchLabels
	deployment.Labels = matchLabels
	return deployment
}

func (w *Workload) buildService() corev1.Service {
	selector := make(map[string]string)
	selector["enovaserving-name"] = w.Spec.Name
	ports := make([]corev1.ServicePort, len(w.Spec.Service.Ports))
	for i, p := range w.Spec.Service.Ports {
		ports[i] = corev1.ServicePort{
			Name:     fmt.Sprintf("tcp%d", i),
			Protocol: corev1.ProtocolTCP,
			Port:     p.Number,
			TargetPort: intstr.IntOrString{
				IntVal: p.Number,
			},
		}
	}

	service := corev1.Service{
		Spec: corev1.ServiceSpec{
			Selector: selector,
			Ports:    ports,
		},
	}
	service.Name = fmt.Sprintf("%s-svc", w.Spec.Name)
	service.Namespace = w.Spec.Namespace
	return service
}

func (w *Workload) buildIngress() networkingv1.Ingress {
	ingressClsName := "nginx"
	acutalPaths := make([]networkingv1.HTTPIngressPath, len(w.Spec.Ingress.Paths))
	rules := make([]networkingv1.IngressRule, 1)

	for i, p := range w.Spec.Ingress.Paths {
		pathType := networkingv1.PathTypePrefix

		acutalPaths[i] = networkingv1.HTTPIngressPath{
			Path:     p.Path,
			PathType: &pathType,
			Backend: networkingv1.IngressBackend{
				Service: &networkingv1.IngressServiceBackend{
					Name: fmt.Sprintf("%s-svc", w.Spec.Name),
					Port: networkingv1.ServiceBackendPort{
						Number: p.Backend.Service.Port.Number,
					},
				},
			},
		}
	}
	rules[0] = networkingv1.IngressRule{
		IngressRuleValue: networkingv1.IngressRuleValue{
			HTTP: &networkingv1.HTTPIngressRuleValue{
				Paths: acutalPaths,
			},
		},
	}
	ingress := networkingv1.Ingress{
		Spec: networkingv1.IngressSpec{
			IngressClassName: &ingressClsName,
			Rules:            rules,
		},
	}
	ingress.Name = fmt.Sprintf("%s-ingress", w.Spec.Name)
	ingress.Annotations = w.Spec.Ingress.Annotations
	return ingress
}

func formatBrokers(brokers []string) string {
	if len(brokers) == 0 {
		return "[]"
	}
	formatted := `["`
	for i, broker := range brokers {
		if i > 0 {
			formatted += `", "`
		}
		formatted += broker
	}
	formatted += `"]`
	return formatted
}

func (w *Workload) buildCollector() otalv1.OpenTelemetryCollector {
	processors := otalv1.AnyConfig{Object: map[string]interface{}{
		"batch": map[string]interface{}{},
		"attributes/metrics": map[string]interface{}{
			"actions": []interface{}{
				map[string]interface{}{
					"key":    "cluster_id",
					"action": "insert",
					"value":  w.Spec.Collector.ClusterId,
				},
			},
		},
		"attributes/http": map[string]interface{}{
			"actions": []interface{}{
				map[string]interface{}{
					"action": "delete",
					"key":    "http.server_name",
				},
				map[string]interface{}{
					"action": "delete",
					"key":    "http.host",
				},
			},
		},
	},
	}

	service := otalv1.Service{
		Extensions: nil,
		Telemetry:  nil,
		Pipelines: map[string]*otalv1.Pipeline{
			"traces": {
				Receivers:  []string{"otlp"},
				Processors: []string{"batch"},
				Exporters:  []string{"kafka"},
			},
			"metrics": {
				Receivers:  []string{"prometheus", "otlp"},
				Processors: []string{"attributes/metrics", "attributes/http", "batch"},
				Exporters:  []string{"kafka"},
			},
		},
	}

	collector := otalv1.OpenTelemetryCollector{
		Spec: otalv1.OpenTelemetryCollectorSpec{
			OpenTelemetryCommonFields: otalv1.OpenTelemetryCommonFields{ServiceAccount: collectorServiceAccount},
			Config:                    otalv1.Config{Processors: &processors, Service: service},
		},
	}
	collector.Name = w.Spec.Name
	collector.Namespace = w.Spec.Namespace
	return collector
}

func (w *Workload) GetDeployment() (*v1.Deployment, error) {
	return w.K8sCli.K8sClient.AppsV1().Deployments(w.Spec.Namespace).Get(w.K8sCli.Ctx, w.Spec.Name, metav1.GetOptions{})
}

func (w *Workload) GetPodsList() (*corev1.PodList, error) {
	opts := metav1.ListOptions{
		LabelSelector: fmt.Sprintf("enovaserving-name=%s", w.Spec.Name),
	}
	return w.K8sCli.K8sClient.CoreV1().Pods(w.Spec.Namespace).List(w.K8sCli.Ctx, opts)
}

func (w *Workload) GetService() (*corev1.Service, error) {
	opts := metav1.GetOptions{}
	service := w.buildService()
	ret, err := w.K8sCli.K8sClient.CoreV1().Services(w.Spec.Namespace).Get(w.K8sCli.Ctx, service.Name, opts)
	if err != nil {
		logger.Errorf("Workload GetService error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) GetIngress() (*networkingv1.Ingress, error) {
	opts := metav1.GetOptions{}
	ingress := w.buildIngress()
	ret, err := w.K8sCli.K8sClient.NetworkingV1().Ingresses(w.Spec.Namespace).Get(w.K8sCli.Ctx, ingress.Name, opts)
	if err != nil {
		logger.Errorf("Workload GetIngress error: %v", err)
		return ret, err
	}
	return ret, nil
}

func (w *Workload) GetCollector() (otalv1.OpenTelemetryCollector, error) {
	collector := otalv1.OpenTelemetryCollector{}
	rsc := w.GetOtCollectorResource()
	ret, err := rsc.Namespace(w.Spec.Namespace).Get(w.K8sCli.Ctx, w.Spec.Name, metav1.GetOptions{})
	if err != nil {
		logger.Errorf("GetCollector Get error: %v", err)
		return collector, err
	}
	_ = mapstructure.Decode(ret.Object, &collector)
	return collector, err
}

func (w *Workload) CreateCollector() (otalv1.OpenTelemetryCollector, error) {
	collector := w.buildCollector()

	obj := w.buildCollectorUnstructued(collector)

	rsc := w.GetOtCollectorResource()
	ret, err := rsc.Namespace(w.Spec.Namespace).Create(w.K8sCli.Ctx, &obj, metav1.CreateOptions{})
	if err != nil {
		logger.Errorf("CreateCollector Create error: %v", err)
		return collector, err
	}
	_ = mapstructure.Decode(&ret.Object, &collector)
	return collector, err
}

func (w *Workload) DeleteCollector() error {
	rsc := w.GetOtCollectorResource()
	if err := rsc.Namespace(w.Spec.Namespace).Delete(w.K8sCli.Ctx, w.Spec.Name, metav1.DeleteOptions{}); client.IgnoreNotFound(err) != nil {
		return err
	}
	return nil
}

func (w *Workload) UpdateCollector() (otalv1.OpenTelemetryCollector, error) {
	collector := w.buildCollector()

	obj := w.buildCollectorUnstructued(collector)

	rsc := w.GetOtCollectorResource()
	ret, err := rsc.Namespace(w.Spec.Namespace).Update(w.K8sCli.Ctx, &obj, metav1.UpdateOptions{})
	if err != nil {
		logger.Errorf("UpdateCollector Update error: %v", err)
		return collector, err
	}
	_ = mapstructure.Decode(&ret.Object, &collector)
	return collector, err
}

func (w *Workload) buildCollectorUnstructued(collector otalv1.OpenTelemetryCollector) unstructured.Unstructured {
	return unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "opentelemetry.io/v1beta1",
			"kind":       "OpenTelemetryCollector",
			"metadata": map[string]interface{}{
				"name":      collector.Name,
				"namespace": collector.Namespace,
			},
			"spec": map[string]interface{}{
				"serviceAccount": collector.Spec.ServiceAccount,
				"config": map[string]interface{}{
					"receivers": map[string]interface{}{
						"otlp": map[string]interface{}{
							"protocols": map[string]interface{}{
								"grpc": map[string]interface{}{
									"endpoint": "0.0.0.0:4317",
								},
								"http": map[string]interface{}{
									"endpoint": "0.0.0.0:4318",
								},
							},
						},
						"prometheus": map[string]interface{}{
							"config": map[string]interface{}{
								"scrape_configs": []interface{}{
									map[string]interface{}{
										"job_name":        "enovaserving",
										"scrape_interval": "5s",
										"static_configs": []interface{}{
											map[string]interface{}{
												"targets": []string{fmt.Sprintf("%s-svc", w.Spec.Name) + ".emergingai.svc.cluster.local:9199"}},
										},
									},
								},
							},
						},
					},
					"exporters": map[string]interface{}{
						"kafka": map[string]interface{}{
							"brokers":          w.Spec.Collector.Kafka.Brokers,
							"topic":            "k8s-common-collector",
							"protocol_version": "2.0.0",
							"auth": map[string]interface{}{
								"sasl": map[string]interface{}{
									"mechanism": "PLAIN",
									"username":  w.Spec.Collector.Kafka.Username,
									"password":  w.Spec.Collector.Kafka.Password,
								},
							},
						},
					},
					"processors": collector.Spec.Config.Processors,
					"service":    collector.Spec.Config.Service,
				},
			},
		},
	}
}

func (w *Workload) GetOtCollectorResource() dynamic.NamespaceableResourceInterface {
	gvr := schema.GroupVersionResource{
		Group:    "opentelemetry.io",
		Version:  "v1beta1",
		Resource: "opentelemetrycollectors",
	}
	return w.K8sCli.DynamicClient.Resource(gvr)
}
