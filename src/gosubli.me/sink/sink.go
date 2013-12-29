package sink

import (
	"io"
	"sync"
)

// Sink implements a sink into which chunks of data are buffered.
// Data written using Writer is split into chunks by newlines(\n or \r\n) and carriage returns(\r)
type Sink struct {
	writer
	d struct {
		sync.Mutex
		chunks [][]byte
	}
}

// Put puts p in the sink.
// Put returns ErrClosed if the sink is closed.
func (s *Sink) Put(p []byte) error {
	if s.closed() {
		return ErrClosed
	}
	s.d.Lock()
	defer s.d.Unlock()
	s.d.chunks = append(s.d.chunks, cp(p))
	return nil
}

// Drain returns all chunks of data that was put into the sink and an error, if any.
// Drain returns an empty slice (that migt be nil) if there is currently no stored data.
// Drain returns io.EOF if the sink is closed and there is no stored data.
func (s *Sink) Drain() ([][]byte, error) {
	s.d.Lock()
	defer s.d.Unlock()

	if len(s.d.chunks) == 0 && s.closed() {
		return nil, io.EOF
	}

	chunks := s.d.chunks
	s.d.chunks = nil
	return chunks, nil
}

// Close closes the sink for further Put()s and Write()s.
// Close returns ErrClosed if the sink is already closed.
func (s *Sink) Close() error {
	return s.close()
}

// NewSink returns a new sink.
func NewSink() *Sink {
	s := &Sink{}
	s.put = s.Put
	return s
}
