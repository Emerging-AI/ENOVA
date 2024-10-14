go install k8s.io/code-generator/cmd/client-gen
export GOPATH=$(go env GOPATH | awk -F ':' '{print $1}')
export PATH=$PATH:$GOPATH/bin
client-gen \
    --input-base="/root/go/pkg/mod/github.com/open-telemetry/opentelemetry-operator@v1.51.0/apis/v1alpha1" \
    --input="" \
    --output-pkg="github.com/Emerging-AI/ENOVA/escaler/pkg/generated/ot/clientset" \
    --output-dir=./pkg/generated/ot/clientset \
    --clientset-name="versioned" \
    --go-header-file="./hack/boilerplate.go.txt"
