package exec

import (
	"gosubli.me/mg"
	"gosubli.me/sink"
	"os/exec"
	"strings"
	"sync"
	"time"
)

var (
	zChunk  = []byte{}
	zChunks = [][]byte{}
)

type StreamResp struct {
	Chunks [][]byte
	Stream string
	End    bool
}

type Resp struct {
	Chunks [][]byte
	Ok     bool
	Dur    string
}

type Switch struct {
	Case        []string
	Negative    bool
	Discard     bool
	Fallthrough bool
}

type Exec struct {
	Cid    string
	Stream string

	Wd            string
	Input         string
	DiscardStdout bool
	DiscardStderr bool
	Env           map[string]string
	Cmd           string
	Args          []string
	Switch        []Switch
	SwitchOk      bool

	brk  *mg.Broker
	sink *sink.Chan
	buf  struct {
		s     [][]byte
		n     int
		merge bool
	}
}

func (e *Exec) Call() (interface{}, string) {
	c := exec.Command(e.Cmd, e.Args...)
	c.Dir = e.Wd
	c.Env = mg.Env(e.Env)
	if !e.DiscardStdout {
		c.Stdout = e.sink
	}
	if !e.DiscardStderr {
		c.Stderr = e.sink
	}
	if e.Input != "" {
		c.Stdin = strings.NewReader(e.Input)
	}

	wg := &sync.WaitGroup{}
	wg.Add(1)
	go e.stream(wg)
	err, dur := procs.Run(e.Cid, c)
	e.sink.Close()
	wg.Wait()
	res := Resp{
		Dur:    dur.String(),
		Chunks: e.chunks(),
		Ok:     c.ProcessState != nil && c.ProcessState.Success(),
	}

	if err != nil {
		return res, err.Error()
	}
	return res, ""
}

func (e *Exec) stream(wg *sync.WaitGroup) {
	defer wg.Done()

	tck := time.NewTicker(500 * time.Millisecond)
	for {
		select {
		case s, ok := <-e.sink.C:
			eof := !ok
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
		Data: StreamResp{
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

func crSuffix(s []byte) bool {
	i := len(s) - 1
	return i >= 0 && s[i] == '\r'
}

func init() {
	mg.Register("exec", func(b *mg.Broker) mg.Caller {
		return &Exec{
			brk:  b,
			sink: sink.NewBufferedChan(100),
		}
	})
}
