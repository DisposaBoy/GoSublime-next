package exec

import (
	"bytes"
	"fmt"
	"go/build"
	"go/parser"
	"go/token"
	"gosubli.me/mg"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

type playState struct {
	*Exec

	tmpDir string
	pkg    *build.Package
}

func (p *playState) saveInput(fn string) error {
	if p.Input == "" {
		return fmt.Errorf("No src")
	}

	if err := ioutil.WriteFile(fn, []byte(p.Input), 0600); err != nil {
		return err
	}

	oldNames := [][]byte{
		[]byte(filepath.Join("_", fn)),
		[]byte(fn),
		[]byte(filepath.Join(".", filepath.Base(fn))),
	}
	newName := []byte(p.Fn)

	p.filter = func(s []byte) []byte {
		for _, old := range oldNames {
			s = bytes.Replace(s, old, newName, -1)
		}
		return s
	}

	return nil
}

func (p *playState) TmpDir() (string, error) {
	if p.tmpDir != "" {
		return p.tmpDir, nil
	}

	dir, err := ioutil.TempDir(mg.TempDir(p.Env), "play-")
	if err != nil {
		return "", err
	}

	p.tmpDir = dir
	p.fini = func() {
		os.RemoveAll(dir)
	}

	return dir, nil
}

func (p *playState) pkgFromInput() (*build.Package, error) {
	tmpDir, err := p.TmpDir()
	if err != nil {
		return nil, err
	}

	fset := token.NewFileSet()
	af, err := parser.ParseFile(fset, p.Fn, p.Input, parser.PackageClauseOnly)
	if err != nil {
		return nil, err
	}

	pkgName := af.Name.String()
	fn := "tmp_test.go"
	if pkgName == "main" {
		fn = "tmp.go"
	}
	fn = filepath.Join(tmpDir, fn)

	if err := p.saveInput(fn); err != nil {
		return nil, err
	}

	p.pkg = &build.Package{
		Name:    pkgName,
		Dir:     tmpDir,
		GoFiles: []string{fn},
	}

	return p.pkg, nil
}

func (p *playState) Pkg() (*build.Package, error) {
	if p.pkg != nil {
		return p.pkg, nil
	}

	if p.Fn == "" || strings.Contains(p.Fn, "gs.view#") {
		return p.pkgFromInput()
	}

	pkg, err := build.ImportDir(filepath.Dir(p.Fn), 0)
	if err != nil {
		return nil, err
	}

	for i, fn := range pkg.GoFiles {
		pkg.GoFiles[i] = filepath.Join(pkg.Dir, fn)
	}
	p.pkg = pkg

	return pkg, err
}

func (p *playState) mainCmd(pkg *build.Package) (*exec.Cmd, error) {
	tmpDir, err := p.TmpDir()
	if err != nil {
		return nil, err
	}

	binFn := filepath.Join(tmpDir, filepath.Base(pkg.Dir)+".exe")
	args := append([]string{"go", "build", "-o", binFn}, pkg.GoFiles...)
	c := exec.Command(args[0], args[1:]...)
	c.Dir = p.Wd
	c.Stdout = p.sink
	c.Stderr = p.sink
	if err := c.Run(); err != nil {
		return nil, fmt.Errorf("Build failed: %#q\nError: `%v`\n", args, err)
	}
	return mkCmd(p.Exec, "", binFn, p.Args...), nil
}

func (p *playState) testCmd(pkg *build.Package) (*exec.Cmd, error) {
	args := append([]string{"test", "-bench", "."}, p.Args...)
	c := mkCmd(p.Exec, "", "go", args...)
	c.Dir = pkg.Dir
	return c, nil
}

func init() {
	virtualCmds.Lock()
	defer virtualCmds.Unlock()

	virtualCmds.m[".play"] = func(e *Exec) (*exec.Cmd, error) {
		p := &playState{Exec: e}
		pkg, err := p.Pkg()
		if err != nil {
			return nil, err
		}

		if pkg.IsCommand() && !strings.HasSuffix(p.Fn, "_test.go") {
			return p.mainCmd(pkg)
		}
		return p.testCmd(pkg)
	}
}
