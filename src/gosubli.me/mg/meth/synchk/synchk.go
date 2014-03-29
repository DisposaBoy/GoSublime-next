package synchk

import (
	"gosubli.me/mg"
	"gosubli.me/mg/sa"
)

type SynChk struct {
	Files []FileRef
}

type FileRef struct {
	Fn  string
	Src string
}

type Res struct {
	Errors []*sa.Error
}

func (s *SynChk) Call() (interface{}, string) {
	res := Res{}
	for _, f := range s.Files {
		if f, _ := sa.Parse(f.Fn, []byte(f.Src)); f != nil {
			res.Errors = append(res.Errors, f.Errors...)
		}
	}
	return res, ""
}

func init() {
	mg.Register("synchk", func(_ *mg.Broker) mg.Caller {
		return &SynChk{}
	})
}
