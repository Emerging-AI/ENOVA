package api

type EnvoaResponse struct {
	Code    int
	Message string
	Result  interface{}
	TraceId string
	Version string
}
