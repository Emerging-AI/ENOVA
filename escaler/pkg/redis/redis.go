package redis

import (
	"context"
	"time"

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

func (r *RedisClient) Set(key string, value string, timeout int64) {
	r.Redis.Set(r.Ctx, key, value, time.Duration(time.Duration(timeout)*time.Microsecond))
}

func (r *RedisClient) Get(key string) string {
	result := r.Redis.Get(r.Ctx, key)
	if result.Err() != nil {
		return ""
	}
	return result.Val()
}

func NewRedisClient(addr string, passwd string, db int) *RedisClient {
	ctx := context.Background()

	rdb := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: passwd,
		DB:       db,
	})

	return &RedisClient{
		Ctx:   ctx,
		Redis: rdb,
	}
}
