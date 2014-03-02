package sink

import (
	"errors"
	"fmt"
	"io"
	"sync"
)

// ErrClosed is the error returned for writes to closed sinks.
var ErrClosed = errors.New("Invalid use of closed sink")

// CloseError stores any errors that may result from closing a sink
type CloseError struct {
	Write error // Write stores any write errors resulting from a close
	Close error // Write stores any close errors resulting from a close
}

type Sink struct {
	closed bool
	buf    []byte
	mu     sync.Mutex
	out    io.WriteCloser
}

// Write writes len(b) bytes to the sink.
// It returns the number of bytes consumed and an error, if any.
// Write returns ErrClosed if the Sink is closed.
func (w *Sink) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	if w.closed {
		return 0, ErrClosed
	}

	var err error
	n := len(p)
	if len(w.buf) != 0 {
		p = append(w.buf, p...)
	}

	for len(p) > 0 && err == nil {
		i := nextChunk(p)
		if i < 0 {
			break
		}
		err = w.writeOut(p[:i])
		p = p[i:]
	}
	w.buf = append(w.buf[:0], p...)
	return n, err
}

// writeOut writes a copy of p to the underlying writer and returns any resultant errors
func (w *Sink) writeOut(p []byte) error {
	_, err := w.out.Write(cp(p))
	return err
}

// Close closes the Sink for further writes and writes any buffered data to the underlying writer.
// Close returns a *CloseError if there were any errors. The Close fields will contain ErrClosed if the error was a result of closing a closed sink
func (w *Sink) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()

	if w.closed {
		return &CloseError{Close: ErrClosed}
	}

	w.closed = true
	e := &CloseError{}
	if len(w.buf) != 0 {
		e.Write = w.writeOut(w.buf)
	}
	w.buf = nil
	e.Close = w.out.Close()

	if e.Write == nil && e.Close == nil {
		return nil
	}
	return e
}

func (c *CloseError) Error() string {
	return fmt.Sprintf("Write: %s, Close: %s", c.Write, c.Close)
}

func nextChunk(p []byte) int {
	for i, c := range p {
		switch {
		case c == '\r' && i > 0:
			return i
		case c == '\n' && i > 1:
			return i
		}
	}
	return -1
}

// cp returns a copy of p.
func cp(p []byte) []byte {
	t := make([]byte, len(p))
	copy(t, p)
	return t
}

// NewSink returns a new Sink that writes data to out in chunks.
// Each chunk will be aligned on newline boundaries e.g. `\nabc` or `\rabc`
func NewSink(out io.WriteCloser) *Sink {
	return &Sink{out: out}
}
