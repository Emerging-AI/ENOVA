package utils

import "reflect"

func GetAllField(s interface{}) []reflect.StructField {
	ret := []reflect.StructField{}
	t := reflect.TypeOf(s)

	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)
		ret = append(ret, field)
	}
	return ret
}
