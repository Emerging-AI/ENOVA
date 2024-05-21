package meta

import "enova/pkg/api"

type TaskStatus string

const (
	TaskStatusCreated    TaskStatus = "created"
	TaskStatusScheduling TaskStatus = "scheduling"
	TaskStatusRunning    TaskStatus = "running"
	TaskStatusError      TaskStatus = "error"
	TaskStatusFinished   TaskStatus = "finished"
)

type DetectTask struct {
	TaskSpec TaskSpecInterface
	Status   TaskStatus
}

type AnomalyRecommendResult struct {
	Timestamp             int64                     `json:"timestamp"`
	IsAnomaly             bool                      `json:"isAnomaly"`
	ConfigRecommendResult api.ConfigRecommendResult `json:"configRecommendResult"`
	CurrentConfig         api.ConfigRecommendResult `json:"currentConfig"`
}

type TaskInfo struct {
	Name   string `json:"name"`
	Status string `json:"status"`
}
