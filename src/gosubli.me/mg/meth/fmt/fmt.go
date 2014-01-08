package mg

import (
	"go/ast"
	"go/parser"
	"gosubli.me/mg"
)

type Res struct {
	Src string
}

type Fmt struct {
	Fn        string
	Src       string
	TabIndent bool
	TabWidth  int
}

func (m *Fmt) Call() (interface{}, string) {
	res := Res{}
	fset, af, err := mg.ParseFile(m.Fn, m.Src, parser.ParseComments)
	if err == nil {
		ast.SortImports(fset, af)
		res.Src, err = mg.Src(fset, af, m.TabIndent, m.TabWidth)
	}
	return res, mg.Err(err)
}

func init() {
	mg.Register("fmt", func(b *mg.Broker) mg.Caller {
		return &Fmt{
			TabIndent: true,
			TabWidth:  8,
		}
	})
}
