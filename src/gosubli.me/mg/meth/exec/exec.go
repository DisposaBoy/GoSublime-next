package exec

import (
	"bytes"
	"fmt"
	"gosubli.me/mg"
	"gosubli.me/sink"
	"os/exec"
	"regexp"
	"strings"
	"sync"
	"time"
)

var (
	zChunk  = []byte{}
	zChunks = [][]byte{}

	caseCache = struct {
		sync.Mutex
		m map[string]*regexp.Regexp
	}{m: map[string]*regexp.Regexp{}}

	virtualCmds = struct {
		sync.Mutex
		m map[string]cmdFactory
	}{m: map[string]cmdFactory{}}

	simpleRepl = strings.NewReplacer(
		`$fn`, `(?P<fn>\S+)`,
		`$pos`, `(?P<pos>[:\d]+)`,
		`$message`, `(?P<message>.+)`,
		`$dirname`, `(?P<dirname>\S+)`,
		`$basename`, `(?P<basename>\W+)`,
	)
)

type cmdFactory func(*Exec) (*exec.Cmd, error)

type StreamRes struct {
	Chunks [][]byte
	Stream string
	End    bool
}

type Res struct {
	Attrs  []Attr
	Chunks [][]byte
	Ok     bool
	Dur    string
	Mem    string
}

type Attr map[string]string

type Switch struct {
	Case        []string
	Negative    bool
	Discard     bool
	Fallthrough bool

	cases []*regexp.Regexp
	attrs []Attr
}

type Exec struct {
	Cid    string
	Stream string

	Wd            string
	Dirty         bool
	Fn            string
	Input         string
	DiscardStdout bool
	DiscardStderr bool
	Env           map[string]string
	Cmd           string
	Args          []string
	Switch        []Switch
	SwitchOk      bool

	filter   func([]byte) []byte
	fini     func()
	switches []*Switch
	brk      *mg.Broker
	sink     *sink.Chan
	buf      struct {
		s     [][]byte
		n     int
		merge bool
	}
}

func (e *Exec) Call() (interface{}, string) {
	e.initSwitches()

	res := Res{}
	wg := &sync.WaitGroup{}
	wg.Add(1)
	go e.stream(wg)

	c, err := e.cmd()
	if err == nil {
		var dur mg.MsDuration
		err, dur = procs.Run(e.Cid, c)
		res.Dur = dur.String()
		res.Mem = maxRss(c.ProcessState)
	}

	if e.fini != nil {
		e.fini()
	}

	e.sink.Close()
	wg.Wait()

	res.Chunks = e.chunks()
	res.Attrs, res.Ok = e.cmdAttrsOk(c)

	return res, mg.Err(err)
}

func (e *Exec) cmd() (*exec.Cmd, error) {
	virtualCmds.Lock()
	f, ok := virtualCmds.m[e.Cmd]
	virtualCmds.Unlock()

	if ok {
		return f(e)
	}
	return mkCmd(e, e.Input, e.Cmd, e.Args...), nil
}

func (e *Exec) stream(wg *sync.WaitGroup) {
	defer wg.Done()

	tck := time.NewTicker(500 * time.Millisecond)
	for {
		select {
		case s, ok := <-e.sink.C:
			if e.filter != nil {
				s = e.filter(s)
			}

			eof := !ok
			s = e.sw(s)
			e.put(s, eof)
			if eof {
				return
			}
		case <-tck.C:
			if len(e.buf.s) != 0 {
				e.flush(false)
			}
		}
	}
}

func (e *Exec) put(s []byte, eof bool) {
	switch {
	case crSuffix(s):
		e.buf.merge = false
		e.buf.s = append(e.buf.s, s)
	case !e.buf.merge || len(e.buf.s) == 0:
		e.buf.merge = true
		e.buf.s = append(e.buf.s, zChunk)
		fallthrough
	default:
		i := len(e.buf.s) - 1
		e.buf.s[i] = append(e.buf.s[i], s...)
	}

	e.buf.n += len(s)
	if eof || e.buf.n >= 32*1024 {
		e.flush(eof)
	}
}

func (e *Exec) chunks() [][]byte {
	if e.buf.s != nil {
		return e.buf.s
	}
	// be nice to the client by not sending them `null` when they expect an array
	return zChunks
}

func (e *Exec) flush(eof bool) {
	if e.Stream == "" {
		return
	}

	e.brk.Send(mg.Response{
		Token: e.Stream,
		Data: StreamRes{
			Chunks: e.chunks(),
			End:    eof,
		},
	})

	for i, s := range e.buf.s {
		e.buf.s[i] = s[:0]
	}
	e.buf.s = e.buf.s[:0]
	e.buf.n = 0
}

func (e *Exec) initSwitches() error {
	for i, _ := range e.Switch {
		sw := &e.Switch[i]
		for _, s := range sw.Case {
			if s != "" {
				rx, err := rx(s)
				if err != nil {
					return err
				}
				sw.cases = append(sw.cases, rx)
			}
		}
		e.switches = append(e.switches, sw)
	}
	return nil
}

func (e *Exec) cmdAttrsOk(c *exec.Cmd) ([]Attr, bool) {
	attrs, swOk := e.collectAttrs()
	if e.SwitchOk && len(e.Switch) > 0 {
		return attrs, swOk
	}
	ok := c != nil && c.ProcessState != nil && c.ProcessState.Success()
	return attrs, ok
}

func (e *Exec) collectAttrs() ([]Attr, bool) {
	attrs := []Attr{}
	ok := true
	for _, sw := range e.switches {
		if len(sw.attrs) > 0 {
			ok = false
			attrs = append(attrs, sw.attrs...)
		}
	}
	return attrs, ok
}

func (e *Exec) sw(s []byte) []byte {
	discard := false

	for _, sw := range e.switches {
		al, matched := sw.match(s)
		sw.attrs = append(sw.attrs, al...)

		if matched != sw.Negative {
			if sw.Discard {
				discard = true
			}

			if !sw.Fallthrough {
				break
			}
		}
	}

	if discard {
		return nil
	}
	return s
}

func (s *Switch) match(p []byte) ([]Attr, bool) {
	if len(s.cases) == 0 {
		return nil, true
	}

	for _, rx := range s.cases {
		ml := rx.FindAllSubmatch(bytes.TrimSpace(p), -1)
		if len(ml) > 0 {
			// p (and by extension ml, mt) is owned by the caller so make sure it gets copied
			names := rx.SubexpNames()
			al := []Attr{}
			for _, mt := range ml {
				attr := Attr{}
				if len(mt) == len(names) {
					for i, k := range names {
						if k != "" {
							attr[k] = string(mt[i])
						}
					}
				}
				if len(mt) != 0 {
					al = append(al, attr)
				}
			}
			return al, true
		}
	}

	return nil, false
}

func rx(s string) (*regexp.Regexp, error) {
	caseCache.Lock()
	defer caseCache.Unlock()

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

func crSuffix(s []byte) bool {
	i := len(s) - 1
	return i >= 0 && s[i] == '\r'
}

func mkCmd(e *Exec, input string, cmd string, args ...string) *exec.Cmd {
	c := exec.Command(cmd, args...)
	c.Dir = e.Wd
	c.Env = mg.Env(e.Env)
	if !e.DiscardStdout {
		c.Stdout = e.sink
	}
	if !e.DiscardStderr {
		c.Stderr = e.sink
	}
	if input != "" {
		c.Stdin = strings.NewReader(input)
	}
	return c
}

func init() {
	mg.Register("exec", func(b *mg.Broker) mg.Caller {
		return &Exec{
			brk:  b,
			sink: sink.NewBufferedChan(100),
		}
	})
}
