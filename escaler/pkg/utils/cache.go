package utils

import (
	"github.com/Emerging-AI/ENOVA/escaler/pkg/redis"
)

type TTLCache interface {
	Set(key string, value string, timeout int64)
	Get(key string) string
}

type RedisTTLCache struct {
	Redis *redis.RedisClient
}

func NewRedisTTLCache(addr string, passwd string, db int) *RedisTTLCache {
	return &RedisTTLCache{
		redis.NewRedisClient(addr, passwd, db),
	}
}

func (r *RedisTTLCache) Set(key string, value string, timeout int64) {
	r.Redis.Set(key, value, timeout)
}

func (r *RedisTTLCache) Get(key string) string {
	return r.Redis.Get(key)
}
