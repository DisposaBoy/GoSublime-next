package intel

import (
	"gosubli.me/mg"
)

type Intel struct {
	InstallSuffix string
	Env           map[string]string
	Dir           string
	Builtins      bool
	Fn            string
	Src           string
	Pos           int
}

func (i *Intel) Call() (interface{}, string) {
	return nil, ""
}

func init() {
	mg.Register("intel", func(_ *mg.Broker) mg.Caller {
		return &Intel{}
	})
}
