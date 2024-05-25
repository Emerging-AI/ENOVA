package logger

import (
	"github.com/Emerging-AI/ENOVA/escaler/pkg/config"
	"github.com/sirupsen/logrus"
)

var logger *logrus.Logger

func init() {
	logger = GetLogger()
}

func GetLogger() *logrus.Logger {
	config := config.GetEConfig()
	logger := logrus.New()

	// 设置日志级别
	switch config.Logger.Level {
	case "panic":
		logrus.SetLevel(logrus.PanicLevel)
	case "fatal":
		logrus.SetLevel(logrus.FatalLevel)
	case "error":
		logrus.SetLevel(logrus.ErrorLevel)
	case "warn", "warning":
		logrus.SetLevel(logrus.WarnLevel)
	case "info":
		logrus.SetLevel(logrus.InfoLevel)
	case "debug":
		logrus.SetLevel(logrus.DebugLevel)
	case "trace":
		logrus.SetLevel(logrus.TraceLevel)
	default:
		logrus.Warn("Unknown log level: ", config.Logger.Level)
		logrus.SetLevel(logrus.InfoLevel) // 设置默认日志等级
	}

	// 设置日志格式
	logger.SetFormatter(&logrus.TextFormatter{
		TimestampFormat: "2006-01-02 15:04:05",
	})
	return logger
}

func Info(args ...interface{}) {
	logger.Infoln(args)
}

func Infof(format string, args ...interface{}) {
	logger.Infof(format, args...)
}

func Debug(args ...interface{}) {
	logger.Debugln(args)
}

func Fatal(args ...interface{}) {
	logger.Fatalln(args)
}

func Warn(args ...interface{}) {
	logger.Warnln(args)
}

func Error(args ...interface{}) {
	logger.Errorln(args)
}

func Errorf(format string, args ...interface{}) {
	logger.Errorf(format, args...)
}

func Panic(args ...interface{}) {
	logger.Panicln(args)
}
