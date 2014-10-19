package gs

import (
	"gosubli.me/mg"
)

const (
	OpenBg = OpenFlag(1 << iota)
)

type OpenFlag int

type OpenOpts struct {
	Fn string
	Bg bool
}

func Open(fn string) {
	OpenFile(fn, 0)
}

func OpenFile(fn string, f OpenFlag) {
	mg.OpenChan.Send(struct {
		Fn string
		Bg bool
	}{
		fn,
		f&OpenBg != 0,
	})
}
