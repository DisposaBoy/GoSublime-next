package sink

import (
	"bytes"
	"errors"
	"sync"
)

// ErrClosed is the error returned for writes to closed sinks.
var ErrClosed = errors.New("Invalid use of closed sink")

type writer struct {
	c struct {
		sync.RWMutex
		closed bool
	}
	b struct {
		sync.Mutex
		buf []byte
	}
	put func([]byte) error
}

// Write writes len(b) bytes to the sink.
// It returns the number of bytes consumed and an error, if any.
// Write returns ErrClosed if the writer is closed.
func (w *writer) Write(p []byte) (int, error) {
	if w.closed() {
		return 0, ErrClosed
	}

	w.b.Lock()
	defer w.b.Unlock()
	n := len(p)

	if len(w.b.buf) > 0 {
		w.b.buf = append(w.b.buf, p...)
		p = w.b.buf[:]
	}

	for len(p) > 0 {
		i := bytes.IndexByte(p, '\n')
		if i >= 0 {
			i++
			if err := w.put(w.cr(p[:i])); err != nil {
				return n, err
			}
			p = p[i:]
		} else {
			p = w.cr(p)
			break
		}
	}
	w.b.buf = append(w.b.buf[:0], p...)
	return n, nil
}

// cr splits p by carriage returns(not \r\n) and passes each chunk to put.
func (w *writer) cr(p []byte) []byte {
	for {
		i := bytes.IndexByte(p, '\r')
		if i < 0 || i == len(p)-1 || p[i+1] == '\n' {
			break
		}
		i++
		if err := w.put(p[:i]); err != nil {
			return p
		}
		p = p[i:]
	}
	return p
}

// closed returns true if the writer is closed.
func (w *writer) closed() bool {
	w.c.RLock()
	defer w.c.RUnlock()
	return w.c.closed
}

// close closes the writer for further writes.
func (w *writer) close() error {
	w.c.Lock()
	defer w.c.Unlock()

	if w.c.closed {
		return ErrClosed
	}
	w.c.closed = true

	var err error
	if len(w.b.buf) > 0 {
		err = w.put(w.b.buf)
		w.b.buf = nil
	}
	return err
}

// cp returns a copy of p.
func cp(p []byte) []byte {
	t := make([]byte, len(p))
	copy(t, p)
	return t
}
