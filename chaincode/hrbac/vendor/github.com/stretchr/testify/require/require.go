package require

import (
	"reflect"
	"strings"
	"testing"
)

func True(t *testing.T, value bool, msgAndArgs ...interface{}) {
	t.Helper()
	if !value {
		t.Fatalf("expected true")
	}
}
func False(t *testing.T, value bool, msgAndArgs ...interface{}) {
	t.Helper()
	if value {
		t.Fatalf("expected false")
	}
}
func NoError(t *testing.T, err error, msgAndArgs ...interface{}) {
	t.Helper()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}
func Error(t *testing.T, err error, msgAndArgs ...interface{}) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected error")
	}
}
func ErrorContains(t *testing.T, err error, contains string, msgAndArgs ...interface{}) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected error containing %q", contains)
	}
	if !strings.Contains(err.Error(), contains) {
		t.Fatalf("expected error %q to contain %q", err.Error(), contains)
	}
}
func Equal(t *testing.T, expected, actual interface{}, msgAndArgs ...interface{}) {
	t.Helper()
	if !reflect.DeepEqual(expected, actual) {
		t.Fatalf("not equal\nexpected: %#v\nactual: %#v", expected, actual)
	}
}
func Contains(t *testing.T, s interface{}, contains interface{}, msgAndArgs ...interface{}) {
	t.Helper()
	if containsValue(s, contains) {
		return
	}
	t.Fatalf("expected %#v to contain %#v", s, contains)
}
func NotContains(t *testing.T, s interface{}, contains interface{}, msgAndArgs ...interface{}) {
	t.Helper()
	if containsValue(s, contains) {
		t.Fatalf("expected %#v not to contain %#v", s, contains)
	}
}

func containsValue(s interface{}, contains interface{}) bool {
	if text, ok := s.(string); ok {
		needle, ok := contains.(string)
		return ok && strings.Contains(text, needle)
	}
	value := reflect.ValueOf(s)
	if value.Kind() != reflect.Slice && value.Kind() != reflect.Array {
		return false
	}
	needle := reflect.ValueOf(contains)
	for i := 0; i < value.Len(); i++ {
		if reflect.DeepEqual(value.Index(i).Interface(), needle.Interface()) {
			return true
		}
	}
	return false
}
