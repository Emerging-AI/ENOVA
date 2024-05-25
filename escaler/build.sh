
go mod download
# go install github.com/swaggo/swag/cmd/swag@latest

# swag init -g cmd/escaler/main.go -o cmd/escaler/docs --parseDependency --parseInternal
mkdir -p dist/bin
go env && go build -o dist/bin/escaler cmd/escaler/main.go
