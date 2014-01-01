package posdef

import (
	"code.google.com/p/go.tools/go/types"
	"code.google.com/p/go.tools/importer"
	"fmt"
	"go/build"
	"gosubli.me/mg"
	"path/filepath"
	"runtime"
	"strings"
)

type Def struct {
	Env           map[string]string
	Fn            string
	InstallSuffix string
	Pos           int
}

type Res struct {
	Fn     string
	Line   int
	Column int
}

func (d *Def) Call() (interface{}, string) {
	if d.Fn == "" {
		return nil, "missing filename"
	}

	gr, err := filepath.Abs(d.Env["GOROOT"])
	if err != nil {
		return nil, err.Error()
	}

	gp, err := filepath.Abs(d.Env["GOPATH"])
	if err != nil {
		return nil, err.Error()
	}

	fn, err := filepath.Abs(d.Fn)
	if err != nil {
		return nil, err.Error()
	}

	dir := filepath.Dir(fn)
	p := ""
	for _, srcDir := range mg.SrcDirs(map[string]string{"GOROOT": gr, "GOPATH": gp}) {
		if strings.HasPrefix(dir, srcDir) {
			p, err = filepath.Rel(srcDir, dir)
			if err != nil {
				return nil, err.Error()
			}
			p = filepath.ToSlash(p)
			break
		}
	}

	if p == "" {
		return nil, fmt.Sprintf("`%v' doesn't appear to be in GOROOT(%v) or GOPATH(%v)", fn, gr, gp)
	}

	bld := &build.Context{
		GOOS:          runtime.GOOS,
		Compiler:      runtime.Compiler,
		GOARCH:        runtime.GOARCH,
		GOROOT:        gr,
		GOPATH:        gp,
		InstallSuffix: d.InstallSuffix,
	}

	imp := importer.New(&importer.Config{
		Build: bld,
		TypeChecker: types.Config{
			FakeImportC: true,
		},
	})

	pkg, err := imp.LoadPackage(p)
	if err != nil {
		return nil, err.Error()
	}

	for id, o := range pkg.Objects {
		p := imp.Fset.Position(id.Pos())
		e := imp.Fset.Position(id.End())
		if p.Offset <= d.Pos && e.Offset >= d.Pos {
			if o != nil {
				p := imp.Fset.Position(o.Pos())
				if p.IsValid() {
					return Res{
						Fn:     p.Filename,
						Line:   p.Line,
						Column: p.Column,
					}, ""
				}
			}
			break
		}
	}
	return nil, ""
}

func init() {
	mg.Register("posdef", func(b *mg.Broker) mg.Caller {
		return &Def{}
	})
}
