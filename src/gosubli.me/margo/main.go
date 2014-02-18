// +build go1.1

package main

import (
	"gosubli.me/mg"
	_ "gosubli.me/mg/meth/declarations"
	_ "gosubli.me/mg/meth/env"
	_ "gosubli.me/mg/meth/exec" // cancel and exec
	_ "gosubli.me/mg/meth/fmt"
	_ "gosubli.me/mg/meth/gocode" // gocode_complete and gocode_calltip
	_ "gosubli.me/mg/meth/hello"
	_ "gosubli.me/mg/meth/ping"
	_ "gosubli.me/mg/meth/posdef"
	_ "gosubli.me/mg/meth/share"
	_ "gosubli.me/mg/meth/synchk"
	"os"
)

func main() {
	mg.Run(os.Args[1:])
}
