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
	put func([]byte) error
}

// Write writes len(b) bytes to the sink.
// It returns the number of bytes consumed and an error, if any.
// Write returns ErrClosed if the writer is closed.
func (w *writer) Write(p []byte) (int, error) {
	if w.closed() {
		return 0, ErrClosed
	}

	for ep := 0; ep < len(p); {
		sp := ep
		if i := bytes.IndexByte(p[sp+1:], '\r'); i >= 0 {
			ep += i + 1
		} else {
			ep = len(p)
		}

		if err := w.put(p[sp:ep]); err != nil {
			return sp, err
		}
	}
	return len(p), nil
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
	return nil
}

// cp returns a copy of p.
func cp(p []byte) []byte {
	t := make([]byte, len(p))
	copy(t, p)
	return t
}
