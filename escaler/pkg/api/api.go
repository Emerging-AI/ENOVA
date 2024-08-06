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

type HttpResponse interface{}

type HeaderBuilderInterface interface {
	Build() (map[string]string, error)
}

type EmptyHeaderBuilder struct {
}

func (hb *EmptyHeaderBuilder) Build() (map[string]string, error) {
	return make(map[string]string), nil
}

type HttpApi[T HttpResponse] struct {
	Method        string
	Url           string
	HeaderBuilder HeaderBuilderInterface
}

func (api *HttpApi[T]) GetRequest(Params interface{}, Headers map[string]string) (*http.Request, error) {
	newHeader, err := api.HeaderBuilder.Build()
	if err != nil {
		logger.Errorf("HeaderBuilder get error: %v", err)
		return nil, err
	}

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

func (api *HttpApi[T]) Call(Params interface{}, Headers map[string]string) (T, error) {
	client := &http.Client{}
	req, err := api.GetRequest(Params, Headers)
	var resp T
	if err != nil {
		return resp, err
	}
	res, err := client.Do(req) // todo 处理err
	if err != nil {
		return resp, err
	}
	return api.processResponse(res)
}

func (api *HttpApi[T]) processResponse(res *http.Response) (T, error) {
	defer res.Body.Close()
	var httpResp T
	if res.StatusCode != http.StatusOK {
		resBody, _ := io.ReadAll(res.Body)
		msg := fmt.Sprintf("HttpApi get StatusOK not ok: status code: %d, resBody: %s", res.StatusCode, resBody)
		logger.Info(msg)
		return httpResp, errors.New(msg)
	}
	resBody, _ := io.ReadAll(res.Body)
	if err := json.Unmarshal(resBody, &httpResp); err != nil {
		logger.Error("Error parsing JSON response: %v", err)
		return httpResp, err
	}
	return httpResp, nil
}
