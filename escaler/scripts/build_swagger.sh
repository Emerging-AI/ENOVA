export GOPATH=$(go env GOPATH | awk -F ':' '{print $1}')
export PATH=$PATH:$GOPATH/bin
swag init -g cmd/escaler/main.go -o cmd/escaler/docs --parseDependency --parseInternal