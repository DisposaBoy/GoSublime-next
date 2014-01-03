// +build go1.1

package main

import (
	"gosubli.me/mg"
	_ "gosubli.me/mg/meth/exec" // cancel and exec
	_ "gosubli.me/mg/meth/hello"
	_ "gosubli.me/mg/meth/ping"
	_ "gosubli.me/mg/meth/posdef"
	"os"
)

func main() {
	mg.Run(os.Args[1:])
}
