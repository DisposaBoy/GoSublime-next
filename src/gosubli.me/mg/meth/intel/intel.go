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
	Types  []string
}

func (i *Intel) Call() (interface{}, string) {
	var err error
	i.Pos = mg.BytePos(i.Src, i.Pos)
	i.fset, i.af, err = mg.ParseFile(i.Fn, i.Src, parser.ParseComments)
	r := &Res{Global: true}
	r.Pkg = i.af.Name.String()
	for _, d := range i.af.Decls {
		switch t := d.(type) {
		case *ast.GenDecl:
			for _, sp := range t.Specs {
				if t, ok := sp.(*ast.TypeSpec); ok && t.Name != nil {
					if _, ignore := t.Type.(*ast.InterfaceType); !ignore {
						r.Types = append(r.Types, t.Name.Name)
					}
				}
			}
		case *ast.FuncDecl:
			p := i.fset.Position(t.Body.Pos()).Offset
			e := i.fset.Position(t.Body.End()).Offset
			if i.Pos >= p && i.Pos <= e {
				r.Global = false
				r.Func = i.funcName(t)
				break
			}
		}
	}
	return r, mg.Err(err)
}

func init() {
	mg.Register("intel", func(_ *mg.Broker) mg.Caller {
		return &Intel{}
	})
}

func (i *Intel) funcName(fun *ast.FuncDecl) string {
	r := fun.Recv
	if r == nil || len(r.List) == 0 {
		return ""
	}

	var id *ast.Ident
	switch t := r.List[0].Type.(type) {
	case *ast.StarExpr:
		switch t := t.X.(type) {
		case *ast.Ident:
			id = t
		}
	case *ast.Ident:
		id = t
	}

	if id != nil {
		return id.Name + "." + fun.Name.Name
	}
	return fun.Name.Name
}
