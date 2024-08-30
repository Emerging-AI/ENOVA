package k8s

import (
	"context"
	"fmt"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
	rscutils "github.com/Emerging-AI/ENOVA/escaler/pkg/resource/utils"
	k8sresource "k8s.io/apimachinery/pkg/api/resource"

	v1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/intstr"

	"k8s.io/client-go/kubernetes"
)

type K8sCli struct {
	K8sClient *kubernetes.Clientset
	Ctx       context.Context
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
	opts := metav1.DeleteOptions{}
	err := w.K8sCli.K8sClient.AppsV1().Deployments(w.Spec.Namespace).Delete(w.K8sCli.Ctx, w.Spec.Name, opts)
	if err != nil {
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
	opts := metav1.DeleteOptions{}
	ingress := w.buildIngress()
	err := w.K8sCli.K8sClient.NetworkingV1().Ingresses(w.Spec.Namespace).Delete(w.K8sCli.Ctx, ingress.Name, opts)
	if err != nil {
		logger.Errorf("Workload DeleteIngress error: %v", err)
		return err
	}
	return nil
}

func (w *Workload) DeleteService() error {
	opts := metav1.DeleteOptions{}
	service := w.buildService()
	err := w.K8sCli.K8sClient.CoreV1().Services(w.Spec.Namespace).Delete(w.K8sCli.Ctx, service.Name, opts)
	if err != nil {
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
							Image:   w.Spec.Image,
							Name:    w.Spec.Name,
							Command: cmd[:1],
							Args:    cmd[1:],
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

	if len(w.Spec.Volumes) > 0 {
		volumes := make([]corev1.Volume, len(w.Spec.Volumes))
		volumeMounts := make([]corev1.VolumeMount, len(w.Spec.Volumes))
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
		deployment.Spec.Template.Spec.Volumes = volumes
		deployment.Spec.Template.Spec.Containers[0].VolumeMounts = volumeMounts
	}
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
			Protocol: corev1.ProtocolSCTP,
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
	service.Name = w.Spec.Service.Name
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
					Name: p.Backend.Service.Name,
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
	return ingress
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