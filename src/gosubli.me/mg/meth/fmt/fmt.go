package mg

import (
	"bytes"
	"go/ast"
	"go/parser"
	"gosubli.me/mg"
	"os"
	"os/exec"
	"strings"
)

type Res struct {
	Src string
}

type Fmt struct {
	Fn        string
	Src       string
	TabIndent bool
	TabWidth  int
	Cmd       string
	Args      []string
}

func (f *Fmt) Call() (interface{}, string) {
	if f.Cmd != "" {
		return f.gofmt()
	}

	res := Res{}
	fset, af, err := mg.ParseFile(f.Fn, f.Src, parser.ParseComments)
	if err == nil {
		ast.SortImports(fset, af)
		res.Src, err = mg.Src(fset, af, f.TabIndent, f.TabWidth)
	}
	return res, mg.Err(err)
}

func (f *Fmt) gofmt() (Res, string) {
	res := Res{}
	c := exec.Command(f.Cmd, f.Args...)
	if f.Src != "" {
		c.Stdin = strings.NewReader(f.Src)
	} else {
		r, err := os.Open(f.Fn)
		if err != nil {
			return res, err.Error()
		}
		c.Stdin = r
		defer r.Close()
	}

	buf := bytes.NewBuffer(nil)
	c.Stdout = buf
	err := c.Run()
	res.Src = buf.String()
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
