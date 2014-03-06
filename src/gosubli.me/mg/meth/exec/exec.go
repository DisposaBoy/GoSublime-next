package exec

import (
	"bytes"
	"gosubli.me/mg"
	"gosubli.me/sink"
	"os/exec"
	"regexp"
	"strings"
	"sync"
)

var (
	virtualCmds = struct {
		sync.Mutex
		m map[string]cmdFactory
	}{m: map[string]cmdFactory{}}

	simpleRepl = strings.NewReplacer(
		`$fn`, `(?P<fn>\S+?)`,
		`$pos`, `(?P<pos>[:\d]+)`,
		`$message`, `(?P<message>.+)`,
		`$dirname`, `(?P<dirname>\S+)`,
		`$basename`, `(?P<basename>\W+)`,
	)
)

type cmdFactory func(*Exec) (*exec.Cmd, error)

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

	fini     func()
	switches []*Switch
	brk      *mg.Broker
	sink     *sink.Sink
	stream   *Stream

	attrs struct {
		sync.Mutex
		matched bool
		list    []Attr
	}
}

func (e *Exec) Call() (interface{}, string) {
	e.stream = NewStream(e)
	e.sink = sink.NewSink(e.stream)
	e.initSwitches()

	res := Res{}
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
	<-e.stream.closed

	res.Chunks = e.stream.chunks()
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
	e.attrs.Lock()
	defer e.attrs.Unlock()
	attrs := e.attrs.list
	e.attrs.list = nil
	return attrs, !e.attrs.matched
}

func (e *Exec) addAttrs(al []Attr) {
	if len(al) == 0 {
		return
	}
	e.attrs.Lock()
	defer e.attrs.Unlock()
	e.attrs.matched = true
	e.attrs.list = append(e.attrs.list, al...)
}

func (e *Exec) sw(s []byte) []byte {
	discard := false

	for _, sw := range e.switches {
		al, matched := sw.match(s)
		e.addAttrs(al)
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
			brk: b,
		}
	})
}
