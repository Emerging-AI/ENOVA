package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
)

type HttpApi struct {
	Method string
	Url    string
}

type EnvoaResponse struct {
	Code    int
	Message string
	Result  interface{}
	TraceId string
	Version string
}

func (api *HttpApi) GetRequest(Params interface{}, Headers map[string]string) (*http.Request, error) {
	newHeader := make(map[string]string)

	// 遍历Headers并将键值对拷贝到newHeader中
	for key, value := range Headers {
		newHeader[key] = value
	}

	logger.Infof("make http request")

	actualMethod := strings.ToUpper(api.Method)
	var requestData io.Reader
	actualUrl := api.Url
	switch actualMethod {
	case "POST", "PUT":
		bytesData, _ := json.Marshal(Params)
		reqBody := string(bytesData)
		logger.Infof("api %s, request body: %s", api.Url, reqBody)
		newHeader["Content-Type"] = "application/json"
		requestData = strings.NewReader(reqBody)
	case "GET", "DELETE":
		Url, _ := url.Parse(api.Url) // todo 处理err
		urlValues := url.Values{}
		if pm, ok := Params.(map[string]string); ok {
			for key, value := range pm {
				urlValues.Set(key, value)
			}
			Url.RawQuery = urlValues.Encode()
			actualUrl = Url.String()
		}

	}

	req, err := http.NewRequest(actualMethod, actualUrl, requestData)
	if err != nil {
		return nil, err
	}
	for key, value := range newHeader {
		req.Header.Add(key, value)
	}
	return req, nil
}

func (api *HttpApi) Call(Params interface{}, Headers map[string]string) (EnvoaResponse, error) {
	client := &http.Client{}
	req, err := api.GetRequest(Params, Headers)
	if err != nil {
		return EnvoaResponse{}, err
	}
	res, err := client.Do(req) // todo 处理err
	if err != nil {
		return EnvoaResponse{}, err
	}
	return api.processResponse(res)
}

func (api *HttpApi) processResponse(res *http.Response) (EnvoaResponse, error) {
	defer res.Body.Close()
	var enovaResp EnvoaResponse
	if res.StatusCode != http.StatusOK {
		resBody, _ := io.ReadAll(res.Body)
		msg := fmt.Sprintf("HttpApi get StatusOK not ok: status code: %d, resBody: %s", res.StatusCode, resBody)
		logger.Info(msg)
		return enovaResp, errors.New(msg)
	}
	resBody, _ := io.ReadAll(res.Body)
	if err := json.Unmarshal(resBody, &enovaResp); err != nil {
		logger.Error("Error parsing JSON response: %v", err)
		return enovaResp, err
	}
	return enovaResp, nil
}
