package share

import (
	"bytes"
	"gosubli.me/mg"
	"io/ioutil"
	"net/http"
)

type Share struct {
	Src string
}

type Res struct {
	Url string
}

func (m Share) Call() (interface{}, string) {
	res := &Res{}
	s := bytes.TrimSpace([]byte(m.Src))
	if len(s) == 0 {
		return res, "Nothing to share"
	}

	u := "http://play.golang.org"
	body := bytes.NewBuffer(s)
	req, err := http.NewRequest("POST", u+"/share", body)
	req.Header.Set("User-Agent", "GoSublime")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return res, err.Error()
	}
	defer resp.Body.Close()

	s, err = ioutil.ReadAll(resp.Body)
	if err != nil {
		return res, err.Error()
	}

	res.Url = u + "/p/" + string(s)
	e := ""
	if resp.StatusCode != 200 {
		e = "Unexpected http status: " + resp.Status
	}

	return res, e
}

func init() {
	mg.Register("share", func(_ *mg.Broker) mg.Caller {
		return &Share{}
	})
}
