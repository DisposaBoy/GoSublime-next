// +build go1.1

package main

import (
	"gosubli.me/mg"
	"os"
)

func main() {
	mg.Run(os.Args[1:])
}
