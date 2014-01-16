package exec

import (
	"bytes"
	"fmt"
	"go/build"
	"gosubli.me/mg"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
)

func playCmd(e *Exec) (*exec.Cmd, error) {
	pkg, err := build.ImportDir(e.Wd, 0)
	if err != nil {
		return nil, err
	}

	if !pkg.IsCommand() {
		args := append([]string{"test"}, e.Args...)
		return mkCmd(e, "", "go", args...), nil
	}

	for i, fn := range pkg.GoFiles {
		pkg.GoFiles[i] = filepath.Join(e.Wd, fn)
	}

	dir, err := ioutil.TempDir(mg.TempDir(e.Env), "play-")
	if err != nil {
		return nil, err
	}

	e.fini = func() {
		os.RemoveAll(dir)
	}

	if e.Dirty {
		tmpFn := filepath.Join(dir, "tmp.go")
		if playInput(e, tmpFn) {
			for i, fn := range pkg.GoFiles {
				if fn == e.Fn {
					pkg.GoFiles[i] = tmpFn
				}
			}
		}
	}

	buf := bytes.NewBuffer(nil)
	binFn := filepath.Join(dir, filepath.Base(e.Wd)+".exe")
	args := append([]string{"go", "build", "-o", binFn}, pkg.GoFiles...)
	c := exec.Command(args[0], args[1:]...)
	c.Stdout = buf
	c.Stderr = buf
	if err := c.Run(); err != nil {
		return nil, fmt.Errorf("build failed: %#q. Error: %v.\nOutput:%v\n", args, err, buf.String())
	}

	return mkCmd(e, "", binFn, e.Args...), nil
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
