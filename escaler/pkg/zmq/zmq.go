package zmq

import (
	"fmt"
	"log"

	"github.com/Emerging-AI/ENOVA/escaler/pkg/logger"
	zmq "github.com/pebbe/zmq4"
)

type ZmqPublisher struct {
	Host      string
	Port      int
	publisher *zmq.Socket
}

type ZmqSubscriber struct {
	Host       string
	Port       int
	subscriber *zmq.Socket
}

func (p *ZmqPublisher) Init() {
	publisher, err := zmq.NewSocket(zmq.PUB)
	if err != nil {
		fmt.Printf("Failed to dial publisher: %v\n", err)
		return
	}
	// 订阅所有消息
	p.publisher = publisher
	if err != nil {
		logger.Error(err)
	}
	address := fmt.Sprintf("tcp://%s:%d", p.Host, p.Port)
	err = p.publisher.Bind(address)
	if err != nil {
		log.Fatal("ZmqPublisher init error: ", err)
		p.Close()
	}
}

func (p *ZmqPublisher) Send(msg string) (bool, error) {
	_, err := p.publisher.Send(msg, 0)

	if err != nil {
		return false, err
	}
	return true, nil
}

func (p *ZmqPublisher) Close() {
	if p.publisher != nil {
		p.publisher.Close()
	}
}

func (s *ZmqSubscriber) Init() {
	subscriber, err := zmq.NewSocket(zmq.SUB)
	topic := ""
	subscriber.SetSubscribe(topic)
	s.subscriber = subscriber
	if err != nil {
		log.Fatal(err)
	}
	address := fmt.Sprintf("tcp://%s:%d", s.Host, s.Port)
	err = subscriber.Connect(address)
	if err != nil {
		log.Fatal(err)
		s.Close()
	}
}

func (s *ZmqSubscriber) Close() {
	if s.subscriber != nil {
		s.subscriber.Close()
	}
}

func (s *ZmqSubscriber) Recv() (string, error) {
	msg, err := s.subscriber.Recv(0)
	return msg, err
}
