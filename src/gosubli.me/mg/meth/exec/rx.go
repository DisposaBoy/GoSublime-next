package exec

import (
	"fmt"
	"regexp"
	"strings"
	"sync"
)

var caseCache = struct {
	sync.Mutex
	m map[string]*regexp.Regexp
}{m: map[string]*regexp.Regexp{}}

var simpleRepl = strings.NewReplacer(
	`$fn`, `(?P<fn>\S+?)`,
	`$pos`, `(?P<pos>[:\d]+)`,
	`$message`, `(?P<message>.+)`,
	`$dirname`, `(?P<dirname>\S+)`,
	`$basename`, `(?P<basename>\W+)`,
)

func rx(s string) (*regexp.Regexp, error) {
	caseCache.Lock()
	defer caseCache.Unlock()

	if !strings.HasPrefix(s, "(?") {
		s = "(?si)" + s
	}

	if rx, ok := caseCache.m[s]; ok {
		return rx, nil
	}

	rx, err := regexp.Compile(simpleRepl.Replace(s))
	if err != nil {
		return nil, fmt.Errorf("cannot compile regexp `%v`: %v", s, err.Error())
	}

	caseCache.m[s] = rx
	return rx, nil
}
