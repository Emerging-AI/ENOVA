package utils

import (
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/meta"
)

func BuildCmdFromTaskSpec(spec meta.TaskSpec) []string {
	cmd := []string{
		"enova", "enode", "run", "--model", spec.Model, "--port", strconv.Itoa(spec.Port), "--host", spec.Host,
		"--backend", spec.Backend,
		"--exporter_endpoint", spec.ExporterEndpoint,
		"--exporter_service_name", spec.ExporterServiceName,
	}

	vllmBackendConfig, ok := spec.BackendConfig.(*meta.VllmBackendConfig)
	if ok {
		jsonBytes, err := json.Marshal(vllmBackendConfig)
		if err != nil {

		} else {
			var vllmBackendConfigMap map[string]interface{}
			err = json.Unmarshal(jsonBytes, &vllmBackendConfigMap)
			if err != nil {

			} else {
				for k, v := range vllmBackendConfigMap {
					cmd = append(cmd, []string{fmt.Sprintf("--%s", k), fmt.Sprintf("%v", v)}...)
				}
			}

		}
	}
	// Add extra enode params
	for k, v := range spec.BackendExtraConfig {
		cmd = append(cmd, []string{fmt.Sprintf("--%s", k), fmt.Sprintf("%v", v)}...)
	}
	return cmd
}
