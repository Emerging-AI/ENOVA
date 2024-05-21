export GOPATH=$(go env GOPATH | awk -F ':' '{print $1}')
export PATH=$PATH:$GOPATH/bin
swag init -g cmd/pilot/pilot.go -o cmd/pilot/docs --parseDependency --parseInternal