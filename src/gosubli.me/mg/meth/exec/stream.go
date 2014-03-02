package exec

import (
	"gosubli.me/mg"
	"sync"
	"time"
)

var (
	streamTimeout = 500 * time.Millisecond
)

type Stream struct {
	mu     sync.Mutex
	token  string
	buf    [][]byte
	n      int
	cr     bool
	brk    *mg.Broker
	filter func([]byte) []byte
	tmr    *time.Timer
	closed chan struct{}
}

type StreamRes struct {
	Chunks [][]byte
	End    bool
}

func (s *Stream) Chunks() [][]byte {
	s.mu.Lock()
	s.mu.Unlock()
	return s.chunks()
}

func (s *Stream) chunks() [][]byte {
	if s.buf != nil {
		return s.buf
	}
	// be nice to the client by not sending them `null` when they expect an array
	return [][]byte{}
}

func (s *Stream) Flush(eof bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.flush(eof)
}

func (s *Stream) flush(eof bool) {
	if s.token == "" {
		return
	}

	s.tmr.Reset(streamTimeout)
	if eof || len(s.buf) != 0 {
		s.brk.Send(mg.Response{
			Token: s.token,
			Data: StreamRes{
				Chunks: s.chunks(),
				End:    eof,
			},
		})
	}

	s.buf = nil
	s.n = 0
	s.cr = false
}

func (s *Stream) Close() error {
	s.Flush(true)
	s.tmr.Stop()
	close(s.closed)
	return nil
}

func (s *Stream) Write(p []byte) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	p = s.filter(p)
	last := len(s.buf) - 1
	isCr := crPfx(p)
	push := last < 0 || (isCr != s.cr)
	s.cr = isCr
	s.n += len(p)

	switch {
	case push:
		s.buf = append(s.buf, p)
	case isCr:
		if s.cr && len(p) <= len(s.buf[last]) {
			s.n -= len(p)
			copy(s.buf[last], p)
		} else {
			s.buf[last] = p
		}
	default:
		s.buf[last] = append(s.buf[last], p...)
	}

	if s.n >= 32*1024 {
		s.flush(false)
	}

	return len(p), nil
}

func crPfx(s []byte) bool {
	return len(s) >= 1 && s[0] == '\r' && (len(s) == 1 || s[1] != '\n')
}

func NewStream(e *Exec) *Stream {
	s := &Stream{
		tmr:    time.NewTimer(streamTimeout),
		brk:    e.brk,
		token:  e.Stream,
		filter: e.sw,
		closed: make(chan struct{}),
	}

	go func() {
		for {
			select {
			case <-s.tmr.C:
				s.Flush(false)
			case <-s.closed:
				return
			}
		}
	}()

	return s
}
