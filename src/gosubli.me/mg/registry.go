package mg

import (
	"runtime"
	"sync"
)

var (
	registry = &Registry{m: map[string]registration{}}
)

type Method func(*Broker) Caller

type Caller interface {
	Call() (res interface{}, err string)
}

type registration struct {
	Method Method
	fn     string
	line   int
}

type Registry struct {
	m       map[string]registration
	methods []string
	lck     sync.RWMutex
}

func Register(name string, method Method) {
	registry.register(name, method, 1)
}

func (r *Registry) Register(name string, method Method) {
	r.register(name, method, 1)
}

func (r *Registry) register(name string, method Method, skip int) {
	r.lck.Lock()
	defer r.lck.Unlock()

	if name == "" {
		logger.Panic("Cannot register method without a name")
	}
	if method == nil {
		logger.Fatalf("Method %v is nil", name)
	}
	if reg, exists := r.m[name]; exists {
		logger.Panicf("Method %v is already registered (from %v:%v)\n", name, reg.fn, reg.line)
	}

	r.methods = append(r.methods, name)
	reg := registration{
		Method: method,
	}
	_, reg.fn, reg.line, _ = runtime.Caller(skip + 1)
	r.m[name] = reg
}

func (r *Registry) Lookup(name string) Method {
	r.lck.RLock()
	defer r.lck.RUnlock()
	return r.m[name].Method
}
