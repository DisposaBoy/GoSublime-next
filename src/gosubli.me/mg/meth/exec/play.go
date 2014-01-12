package exec

import (
	"bytes"
	"go/build"
	"gosubli.me/mg"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
)

func playCmd(e *Exec) []*exec.Cmd {
	dir, err := ioutil.TempDir(mg.TempDir(e.Env), "play-")
	if err != nil {
		return nil
	}

	e.fini = func() {
		os.RemoveAll(dir)
	}

	pkg, err := build.ImportDir(e.Wd, 0)
	if err != nil {
		return nil
	}

	if !pkg.IsCommand() {
		args := append([]string{"test"}, e.Args...)
		return []*exec.Cmd{mkCmd(e, "", "go", args...)}
	}

	srcFn := filepath.Join(dir, "tmp.go")
	if playInput(e, srcFn) {
		for i, s := range pkg.GoFiles {
			if s == e.Fn {
				pkg.GoFiles[i] = srcFn
			}
		}
	}

	return []*exec.Cmd{
		mkCmd(e, "", "go", append([]string{"run"}, pkg.GoFiles...)...),
	}
}

func playInput(e *Exec, fn string) bool {
	if e.Input == "" {
		return false
	}

	err := ioutil.WriteFile(fn, []byte(e.Input), 0644)
	if err != nil {
		return false
	}

	oldNames := [][]byte{
		[]byte(fn),
		[]byte(filepath.Join(".", filepath.Base(fn))),
	}

	new := []byte(e.Fn)
	if len(new) == 0 {
		new = []byte("<stdin>")
	}

	e.filter = func(s []byte) []byte {
		for _, old := range oldNames {
			s = bytes.Replace(s, old, new, -1)
		}
		return s
	}

	return true
}
