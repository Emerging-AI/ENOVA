
go mod download
# go install github.com/swaggo/swag/cmd/swag@latest

# swag init -g cmd/pilot/pilot.go -o cmd/pilot/docs --parseDependency --parseInternal
mkdir -p dist/bin
go env && go build -o dist/bin/pilot cmd/pilot/pilot.go
