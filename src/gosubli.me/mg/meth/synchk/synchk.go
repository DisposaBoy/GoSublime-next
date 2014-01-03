package synchk

import (
	"go/parser"
	"go/scanner"
	"go/token"
	"gosubli.me/mg"
)

type SynChk struct {
	Files []FileRef
}

type FileRef struct {
	Fn  string
	Src string
}

type Error struct {
	Fn      string
	Line    int
	Column  int
	Message string
}

type Res struct {
	Errors []Error
}

func (s *SynChk) Call() (interface{}, string) {
	fset := token.NewFileSet()
	res := Res{
		Errors: []Error{},
	}

	for _, f := range s.Files {
		if f.Fn == "" && f.Src == "" {
			continue
		}

		var src []byte
		if f.Src != "" {
			src = []byte(f.Src)
		}

		_, err := parser.ParseFile(fset, f.Fn, src, parser.DeclarationErrors)
		if el, ok := err.(scanner.ErrorList); ok {
			for _, e := range el {
				res.Errors = append(res.Errors, Error{
					Fn:      e.Pos.Filename,
					Line:    e.Pos.Line,
					Column:  e.Pos.Column,
					Message: e.Msg,
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
