package redis

import (
	"context"
	"enova/pkg/config"

	"github.com/go-redis/redis/v8"
)

type RedisClient struct {
	Ctx   context.Context
	Redis *redis.Client
}

func (r *RedisClient) SetList(key string, values []string) error {
	_, err := r.DelList(key)
	if err != nil {
		return err
	}
	for _, value := range values {
		if err := r.Redis.RPush(r.Ctx, key, value).Err(); err != nil {
			return err
		}
	}
	return nil
}

func (r *RedisClient) GetList(key string) ([]string, error) {
	storedStringArray, err := r.Redis.LRange(r.Ctx, key, 0, -1).Result()
	if err != nil {
		return storedStringArray, err
	}
	return storedStringArray, nil
}

func (r *RedisClient) DelList(key string) (int64, error) {
	return r.Redis.Del(r.Ctx, key).Result()
}

func (r *RedisClient) AppendList(key string, value string) error {
	if err := r.Redis.LPush(r.Ctx, key, value).Err(); err != nil {
		return err
	}
	return nil
}

func (r *RedisClient) AppendListWithLimitSize(key string, value string, limit int64) error {
	if err := r.AppendList(key, value); err != nil {
		return err
	}
	if err := r.Redis.LTrim(r.Ctx, key, 0, limit).Err(); err != nil {
		return err
	}
	return nil
}

func NewRedisClient() *RedisClient {
	ctx := context.Background()

	rdb := redis.NewClient(&redis.Options{
		Addr:     config.GetEConfig().Redis.Addr,
		Password: config.GetEConfig().Redis.Password,
		DB:       config.GetEConfig().Redis.Db,
	})

	return &RedisClient{
		Ctx:   ctx,
		Redis: rdb,
	}
}
