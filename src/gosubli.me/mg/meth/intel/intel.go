package intel

import (
	"go/ast"
	"gosubli.me/mg"
	"gosubli.me/mg/sa"
)

type Intel struct {
	InstallSuffix string
	Env           map[string]string
	Dir           string
	Builtins      bool
	Fn            string
	Src           string
	Pos           int

	f *sa.File
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
	i.f, err = sa.Parse(i.Fn, []byte(i.Src))
	r := &Res{Global: true}
	r.Pkg = i.f.Name.String()
	for _, d := range i.f.Decls {
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
			if i.f.OffsetIn(i.Pos, t.Body) {
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
