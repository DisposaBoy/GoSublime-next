package main

import (
	"time"
)

type mPing struct {
	Delay string
}

func (m *mPing) Call() (interface{}, string) {
	start := time.Now()

	if m.Delay != "" {
		d, _ := time.ParseDuration(m.Delay)
		time.Sleep(d)
	}

	return M{
		"start": start.String(),
		"end":   time.Now().String(),
	}, ""
}

func init() {
	registry.Register("ping", func(_ *Broker) Caller {
		return &mPing{}
	})
}
