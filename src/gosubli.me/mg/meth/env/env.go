package env

import (
	"gosubli.me/mg"
	"os"
	"strings"
)

var (
	defaultEnv = mg.DefaultEnv()
)

type Env struct {
	List   []string
	Gopath string
}

func mEnvGetEnv(k string) string {
	v := os.Getenv(k)
	if v == "" {
		v = defaultEnv[k]
	}
	return v
}

func (m *Env) Call() (interface{}, string) {
	env := map[string]string{}

	if len(m.List) == 0 {
		for k, v := range defaultEnv {
			env[k] = v
		}

		for _, s := range os.Environ() {
			p := strings.SplitN(s, "=", 2)
			if len(p) == 2 {
				env[p[0]] = p[1]
			} else {
				env[p[0]] = ""
			}
		}
	} else {
		for _, k := range m.List {
			env[k] = mEnvGetEnv(k)
		}
	}

	return env, ""
}

func init() {
	mg.Register("env", func(_ *mg.Broker) mg.Caller {
		return &Env{}
	})
}
