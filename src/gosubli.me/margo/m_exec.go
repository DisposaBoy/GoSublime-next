package main

type Switch struct {
	Case        string
	Attr        map[string]interface{}
	Negative    bool
	Discard     bool
	Fallthrough bool
}

type mExec struct {
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

	b     *Broker
}

func (m *mExec) Call() (interface{}, string) {
	return nil, "N/I"
}

func init() {
	registry.Register("exec", func(b *Broker) Caller {
		return &mExec{
			b: b,
		}
	})
}
