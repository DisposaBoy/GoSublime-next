package ping

import (
	"gosubli.me/mg"
	"time"
)

type Ping struct {
	Delay string
}

func (p *Ping) Call() (interface{}, string) {
	start := time.Now()

	if p.Delay != "" {
		d, _ := time.ParseDuration(p.Delay)
		time.Sleep(d)
	}

	return mg.M{
		"start": start.String(),
		"end":   time.Now().String(),
	}, ""
}

func init() {
	mg.Register("ping", func(_ *mg.Broker) mg.Caller {
		return &Ping{}
	})
}
