package sa

import (
	"go/ast"
	"go/parser"
	"go/scanner"
	"go/token"
	"gosubli.me/something-borrowed/blake2b"
	"io/ioutil"
	"sync"
)

const (
	DefaultMode = parser.ParseComments | parser.DeclarationErrors | parser.AllErrors
)

var (
	cache = struct {
		sync.RWMutex
		files fileMap
	}{
		files: fileMap{},
	}
)

type (
	cKey [64]byte

	fileMap map[cKey]*cFile

	cFile struct {
		*ast.File
		Fset   *token.FileSet
		Errors scanner.ErrorList
	}

	File struct {
		*cFile
		Fn  string
		Src []byte
	}
)

func (f *File) Position(p token.Pos) token.Position {
	return f.Fset.Position(p)
}

func (f *File) OffsetIn(i int, n ast.Node) bool {
	p := f.Fset.Position(n.Pos()).Offset
	e := f.Fset.Position(n.End()).Offset
	return i >= p && i <= e
}

func Parse(fn string, s []byte) (*File, error) {
	var err error
	if len(s) == 0 {
		if s, err = ioutil.ReadFile(fn); err != nil {
			return nil, err
		}
	}
	cf, err := lk(fn, s)
	f := &File{
		cFile: cf,
		Fn:    fn,
		Src:   s,
	}
	return f, err
}

func lk(fn string, s []byte) (*cFile, error) {
	k := cKey(blake2b.Sum512(s))
	cache.RLock()
	cf, ok := cache.files[k]
	cache.RUnlock()
	if ok {
		return cf, nil
	}
	return mk(k, fn, s)
}

func mk(k cKey, fn string, s []byte) (*cFile, error) {
	fset := token.NewFileSet()
	af, err := parser.ParseFile(fset, fn, s, DefaultMode)
	if af == nil {
		return nil, err
	}
	f := &cFile{
		File: af,
		Fset: fset,
	}

	if el, ok := err.(scanner.ErrorList); ok {
		f.Errors = el
	}

	cache.Lock()
	cache.files[k] = f
	cache.Unlock()
	return f, nil
}
