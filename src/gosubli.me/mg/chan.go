package mg

var (
	StatusChan = Chan("margo.status")
	OpenChan   = Chan("margo.open")
)

type Chan string

func (c Chan) Send(data interface{}) {
	post(Response{
		Token: string(c),
		Data:  data,
	})
}
