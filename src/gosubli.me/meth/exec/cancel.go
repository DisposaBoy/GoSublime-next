package exec

import (
	"gosubli.me/mg"
	"time"
)

type Cancel struct {
	Cid string
}

func (c *Cancel) Call() (interface{}, string) {
	start := time.Now()
	procs.Cancel(c.Cid)
	res := mg.M{
		c.Cid: true,
		"dur": mg.Since(start).String(),
	}
	return res, ""
}

func init() {
	mg.Register("cancel", func(b *mg.Broker) mg.Caller {
		return &Cancel{}
	})
}
