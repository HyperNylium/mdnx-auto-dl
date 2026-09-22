package main

import (
	"bytes"
	"compress/flate"
	"compress/gzip"
	"compress/zlib"
	"context"
	"encoding/base64"
	"errors"
	"io"
	"net/url"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/andybalholm/brotli"
	http "github.com/bogdanfinn/fhttp"
	"github.com/klauspost/compress/zstd"
)

type engine struct {
	mu         sync.Mutex
	transports map[string]*http.Transport
}

func newEngine() *engine {
	return &engine{transports: map[string]*http.Transport{}}
}

func (e *engine) close() {
	e.mu.Lock()
	defer e.mu.Unlock()

	for _, t := range e.transports {
		t.CloseIdleConnections()
	}
}

func (e *engine) transport(doh string) (*http.Transport, error) {
	if doh == "" {
		doh = os.Getenv("ZLO_EDGE_DOH_URL")
	}

	e.mu.Lock()
	defer e.mu.Unlock()

	if transport := e.transports[doh]; transport != nil {
		return transport, nil
	}

	if len(e.transports) >= 8 {
		return nil, errors.New("Too many transport configurations")
	}

	resolver, err := newECHResolver(doh)
	if err != nil {
		return nil, err
	}

	transport, err := newTransport(resolver)
	if err != nil {
		return nil, err
	}

	e.transports[doh] = transport

	return transport, nil
}

var errRedirect = errors.New("redirect rejected")
var errRedirectLimit = errors.New("redirect limit")
var errBodyLimit = errors.New("body limit")

func validURL(raw string) (*url.URL, error) {
	u, err := url.Parse(raw)
	if err != nil || u.Hostname() == "" || u.User != nil || (u.Scheme != "https" && u.Scheme != "http") {
		return nil, errors.New("Expected an HTTP or HTTPS URL without embedded credentials")
	}

	return u, nil
}

func origin(u *url.URL) string {
	port := u.Port()

	if port == "" {
		if u.Scheme == "https" {
			port = "443"
		} else {
			port = "80"
		}
	}

	return strings.ToLower(u.Scheme + "://" + u.Hostname() + ":" + port)
}

func sensitiveHeader(key string) bool {
	switch strings.ToLower(key) {
	case "authorization", "proxy-authorization", "cookie", "cookie2":
		return true
	}

	return false
}

func (e *engine) execute(ctx context.Context, message requestMessage) responseMessage {
	fail := func(code, text string) responseMessage {
		return errorResponse(message.ID, code, text)
	}

	u, err := validURL(message.URL)
	if err != nil {
		return fail("INVALID_REQUEST", err.Error())
	}

	if message.Method == "" {
		message.Method = "GET"
	}

	if message.Redirect == "" {
		message.Redirect = "follow"
	}

	if message.Redirect != "follow" && message.Redirect != "manual" && message.Redirect != "error" {
		return fail("INVALID_REQUEST", "Invalid redirect mode")
	}

	if len(message.Body) > base64.StdEncoding.EncodedLen(maxBody) {
		return fail("BODY_TOO_LARGE", "Request exceeds 64 MiB")
	}

	body, err := base64.StdEncoding.DecodeString(message.Body)
	if err != nil {
		return fail("INVALID_REQUEST", "Invalid base64 request body")
	}

	if len(body) > maxBody {
		return fail("BODY_TOO_LARGE", "Request exceeds 64 MiB")
	}

	if message.TimeoutMs <= 0 {
		message.TimeoutMs = 30000
	}

	ctx, cancel := context.WithTimeout(ctx, time.Duration(message.TimeoutMs)*time.Millisecond)
	defer cancel()

	request, err := http.NewRequestWithContext(ctx, message.Method, u.String(), bytes.NewReader(body))
	if err != nil {
		return fail("INVALID_REQUEST", "Invalid request method or URL")
	}

	for _, header := range message.Headers {
		name := strings.ToLower(header[0])

		// Host is always derived from the current URL, including redirects.
		if name == "host" {
			continue
		}

		request.Header[name] = append(request.Header[name], header[1])
		request.Header[http.HeaderOrderKey] = append(request.Header[http.HeaderOrderKey], name)
	}

	transport, err := e.transport(message.DoHURL)
	if err != nil {
		return fail("INVALID_CONFIGURATION", "Invalid transport or DNS configuration")
	}

	redirected := false
	credentialsStripped := false

	client := &http.Client{
		Transport: transport,
		CheckRedirect: func(next *http.Request, via []*http.Request) error {
			if message.Redirect == "manual" {
				return http.ErrUseLastResponse
			}

			if message.Redirect == "error" {
				return errRedirect
			}

			if len(via) >= 20 {
				return errRedirectLimit
			}

			if _, err := validURL(next.URL.String()); err != nil {
				return errRedirect
			}

			if origin(next.URL) != origin(via[len(via)-1].URL) {
				credentialsStripped = true
			}

			if credentialsStripped {
				for key := range next.Header {
					if sensitiveHeader(key) {
						delete(next.Header, key)
					}
				}
			}

			next.Host = next.URL.Host

			for key := range next.Header {
				if strings.EqualFold(key, "host") {
					delete(next.Header, key)
				}
			}

			redirected = true

			return nil
		},
	}

	response, err := client.Do(request)
	if err != nil {
		if errors.Is(ctx.Err(), context.Canceled) {
			return fail("ABORT_ERR", "Request cancelled")
		}

		if errors.Is(ctx.Err(), context.DeadlineExceeded) {
			return fail("TIMEOUT_ERR", "Request timed out")
		}

		if errors.Is(err, errRedirectLimit) {
			return fail("REDIRECT_ERR", "Too many redirects")
		}

		if errors.Is(err, errRedirect) {
			return fail("REDIRECT_ERR", "Redirect is not allowed")
		}

		return fail("NETWORK_ERR", "Edge transport connection failed")
	}

	defer response.Body.Close()

	decoded, err := readResponseBody(response)
	if err != nil {
		if errors.Is(ctx.Err(), context.Canceled) {
			return fail("ABORT_ERR", "Request cancelled")
		}

		if errors.Is(ctx.Err(), context.DeadlineExceeded) {
			return fail("TIMEOUT_ERR", "Request timed out")
		}

		if errors.Is(err, errBodyLimit) {
			return fail("BODY_TOO_LARGE", "Response exceeds 64 MiB")
		}

		return fail("NETWORK_ERR", "Unable to read response body")
	}

	keys := make([]string, 0, len(response.Header))

	for key := range response.Header {
		keys = append(keys, key)
	}

	sort.Strings(keys)
	headers := make([][2]string, 0, len(keys))

	for _, key := range keys {
		for _, value := range response.Header[key] {
			headers = append(headers, [2]string{key, value})
		}
	}

	return responseMessage{
		ID:             message.ID,
		Status:         response.StatusCode,
		StatusText:     http.StatusText(response.StatusCode),
		Headers:        headers,
		Body:           decoded,
		BinaryResponse: message.BinaryResponse,
		URL:            response.Request.URL.String(),
		Redirected:     redirected,
	}
}

func limitedBody(reader io.Reader) ([]byte, error) {
	data, err := io.ReadAll(io.LimitReader(reader, maxBody+1))
	if err == nil && len(data) > maxBody {
		return nil, errBodyLimit
	}

	return data, err
}

func readResponseBody(response *http.Response) ([]byte, error) {
	data, err := limitedBody(response.Body)
	if err != nil {
		return nil, err
	}

	if len(data) == 0 {
		return data, nil
	}

	encodings := strings.Split(strings.ToLower(response.Header.Get("Content-Encoding")), ",")

	for i := len(encodings) - 1; i >= 0; i-- {
		var reader io.Reader
		var closer io.Closer

		switch strings.TrimSpace(encodings[i]) {
		case "", "identity":
			continue
		case "gzip":
			r, e := gzip.NewReader(bytes.NewReader(data))
			if e != nil {
				return nil, e
			}

			reader = r
			closer = r
		case "deflate":
			r, e := zlib.NewReader(bytes.NewReader(data))
			if e != nil {
				r = flate.NewReader(bytes.NewReader(data))
			}

			reader = r
			closer = r
		case "br":
			reader = brotli.NewReader(bytes.NewReader(data))
		case "zstd":
			r, e := zstd.NewReader(bytes.NewReader(data), zstd.WithDecoderMaxMemory(maxBody), zstd.WithDecoderConcurrency(1))
			if e != nil {
				return nil, e
			}

			data, e = limitedBody(r)
			r.Close()

			if e != nil {
				return nil, e
			}

			continue
		default:
			return nil, errors.New("unsupported content encoding")
		}

		data, err = limitedBody(reader)

		if closer != nil {
			closer.Close()
		}

		if err != nil {
			return nil, err
		}
	}

	return data, nil
}
