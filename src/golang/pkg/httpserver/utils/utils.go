package utils

import (
	"reflect"
	"strconv"
)

func HasMethod(s interface{}, methodName string) bool {
	typ := reflect.TypeOf(s)
	_, ok := typ.MethodByName(methodName)
	return ok
}

// ParseUnixTimestamp
func ParseUnixTimestamp(ts int64) string {
	if ts >= (1 << 32) {
		// The timestamp is in milliseconds. Convert it to seconds.
		ts /= 1000
	}
	return strconv.FormatFloat(float64(ts), 'g', -1, 64)
}
