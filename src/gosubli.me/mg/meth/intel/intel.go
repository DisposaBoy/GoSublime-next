package intel

import (
	"go/ast"
	"go/parser"
	"go/token"
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

	fset *token.FileSet
	af   *ast.File
}

type Res struct {
	Global bool
	Func   string
	Pkg    string
}

func (i *Intel) Call() (interface{}, string) {
	r := Res{}
	r.Global, r.Func = i.gf()
	if i.af != nil {
		r.Pkg = i.af.Name.String()
	}
	return r, ""
}

func (i *Intel) init() {
	i.Pos = mg.BytePos(i.Src, i.Pos)
	i.fset, i.af, _ = mg.ParseFile(i.Fn, i.Src, parser.ParseComments)
}

func init() {
	mg.Register("intel", func(_ *mg.Broker) mg.Caller {
		return &Intel{}
	})
}

func (i *Intel) gf() (bool, string) {
	g := true
	f := ""

	if i.af == nil {
		return g, f
	}

	for _, d := range i.af.Decls {
		switch fun := d.(type) {
		case *ast.FuncDecl:
			p := i.fset.Position(fun.Body.Pos()).Offset
			e := i.fset.Position(fun.Body.End()).Offset
			if i.Pos >= p && i.Pos <= e {
				g = false
				if r := fun.Recv; r != nil && len(r.List) > 0 {
					switch t := r.List[0].Type.(type) {
					case *ast.StarExpr:
						switch t := t.X.(type) {
						case *ast.Ident:
							f = t.Name + "."
						}
					case *ast.Ident:
						f = t.Name + "."
					}
				}
				f += fun.Name.String()
				break
			}
		}
	}

	return g, f
}
