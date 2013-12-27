package mg

import (
	"time"
)

type mCancel struct {
	Cid string
}

func (m *mCancel) Call() (interface{}, string) {
	start := time.Now()
	procs.Cancel(m.Cid)
	res := M{
		m.Cid: true,
		"dur": msDur(start).String(),
	}
	return res, ""
}

func init() {
	registry.Register("cancel", func(b *Broker) Caller {
		return &mCancel{}
	})
}
