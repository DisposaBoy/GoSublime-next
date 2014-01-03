package mg

import (
	"gosubli.me/mg"
)

type Hello mg.M

func (h Hello) Call() (interface{}, string) {
	return h, ""
}

func init() {
	mg.Register("hello", func(_ *mg.Broker) mg.Caller {
		return &Hello{}
	})
}
