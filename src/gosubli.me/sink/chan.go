package sink

// Chan implements a sink that sends chunks of data onto chan C.
// Data written using Write is split into chunks by newlines(\n or \r\n) and carriage returns(\r).
type Chan struct {
	writer
	out chan<- []byte
	C   <-chan []byte
}

// Put sends p on chan C.
// Put returns ErrClosed if the sink is closed.
func (c *Chan) Put(p []byte) error {
	if c.closed() {
		return ErrClosed
	}
	c.out <- cp(p)
	return nil
}

// Close closes the sink for further writes and C for further receives.
// Close rerturns ErrClose if the sink is already closed.
func (c *Chan) Close() error {
	if err := c.close(); err != nil {
		return err
	}
	close(c.out)
	return nil
}

// NewBuffereChan returns a new Chan with C buffered to n chunks of data.
func NewBufferedChan(n int) *Chan {
	ch := make(chan []byte, n)
	c := &Chan{
		out: ch,
		C:   ch,
	}
	c.put = c.Put
	return c
}

// NewBuffereChan returns a new unbuffered chan C
func NewChan() *Chan {
	return NewBufferedChan(0)
}
