package counter

import (
	"strconv"
	"sync/atomic"
)

type N uint64

func (n *N) Next() uint64 {
	return atomic.AddUint64((*uint64)(n), 1)
}

func (n *N) Current() uint64 {
	return atomic.LoadUint64((*uint64)(n))
}

func (n *N) NextStringBase(base int) string {
	return strconv.FormatUint(n.Next(), base)
}

func (n *N) NextString() string {
	return n.NextStringBase(10)
}

func (n *N) CurrentStringBase(base int) string {
	return strconv.FormatUint(n.Current(), base)
}

func (n *N) CurrentString() string {
	return n.CurrentStringBase(10)
}

func New() *N {
	return new(N)
}
