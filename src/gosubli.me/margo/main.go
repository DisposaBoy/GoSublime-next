// +build go1.1

package main

import (
	_ "gosubli.me/meth/exec" // cancel and exec
	_ "gosubli.me/meth/hello"
	_ "gosubli.me/meth/ping"
	"gosubli.me/mg"
	"os"
)

func main() {
	mg.Run(os.Args[1:])
}
