package exec

import (
	"gosubli.me/mg"
)

type Switch struct {
	Case        string
	Attr        map[string]interface{}
	Negative    bool
	Discard     bool
	Fallthrough bool
}

type Exec struct {
	Cid    string
	Stream string

	Wd            string
	Input         string
	DiscardStdout bool
	DiscardStderr bool
	Env           map[string]string
	Cmd           string
	Args          []string
	Switch        []*Switch

	b *mg.Broker
}

func (e *Exec) Call() (interface{}, string) {
	return nil, "N/I"
}

func init() {
	mg.Register("exec", func(b *mg.Broker) mg.Caller {
		return &Exec{
			b: b,
		}
	})
}
