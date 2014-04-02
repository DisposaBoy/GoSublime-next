package mg

import (
	"bytes"
	"gosubli.me/mg"
	"gosubli.me/mg/sa"
	"os"
	"os/exec"
	"strings"
)

type Res struct {
	Src string
}

type Fmt struct {
	Fn   string
	Src  string
	Cmd  string
	Args []string
}

func (f *Fmt) Call() (interface{}, string) {
	if f.Cmd != "" {
		return f.gofmt()
	}

	sf, err := sa.Parse(f.Fn, []byte(f.Src))
	if err != nil {
		return nil, err.Error()
	}

	s := string(sf.Src)
	if s == f.Src {
		s = ""
	}
	return Res{Src: s}, ""
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
		return &Fmt{}
	})
}
