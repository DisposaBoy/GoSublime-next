// +build !go1.1

package main

import (
	"encoding/json"
	"flag"
	"os"
)

func main() {
	// set the old flags for compatibility
	flag.Bool("env", false, "")
	flag.Bool("wait", false, "")
	flag.Int("poll", 0, "")
	flag.String("do", "", "")
	flag.Int("oom", 0, "")

	// we're only interested in `tag` so all others ar ignored
	tag := flag.String("tag", "", "")
	flag.Parse()

	var req struct {
		Token string `json:"token"`
	}

	var res struct {
		Token string `json:"token"`
		Error string `json:"error"`
		Tag   string `json:"tag"`
	}

	res.Tag = *tag
	res.Error = "go1.0 is not supported. Please update your Go installation. See http://golang.org/doc/install"
	dec := json.NewDecoder(os.Stdin)
	enc := json.NewEncoder(os.Stdout)

	for {
		if err := dec.Decode(&req); err != nil {
			break
		}
		res.Token = req.Token
		enc.Encode(res)
		os.Stdout.WriteString("\n")
	}
}
