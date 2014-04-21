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
		if sf, _ := sa.Parse(f.Fn, []byte(f.Src)); sf != nil {
			for _, e := range sf.Errors {
				res.Errors = append(res.Errors, &sa.Error{
					Fn:      f.Fn,
					Line:    e.Line,
					Column:  e.Column,
					Offset:  e.Offset,
					Message: e.Message,
				})
			}
		}
	}
	return res, ""
}

func init() {
	mg.Register("synchk", func(_ *mg.Broker) mg.Caller {
		return &SynChk{}
	})
}
