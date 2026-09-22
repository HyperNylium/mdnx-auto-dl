package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sync"
)

const maxBody = 64 << 20
const maxFrame = 90 << 20

type requestMessage struct {
	ID             string      `json:"id"`
	Type           string      `json:"type"`
	URL            string      `json:"url"`
	Method         string      `json:"method"`
	Headers        [][2]string `json:"headers"`
	Body           string      `json:"body"`
	Redirect       string      `json:"redirect"`
	TimeoutMs      int         `json:"timeoutMs"`
	DoHURL         string      `json:"dohUrl"`
	BinaryResponse bool        `json:"binaryResponse"`
}

type responseMessage struct {
	ID             string         `json:"id"`
	Status         int            `json:"status,omitempty"`
	StatusText     string         `json:"statusText,omitempty"`
	Headers        [][2]string    `json:"headers,omitempty"`
	Body           []byte         `json:"body"`
	BodyLength     *int           `json:"bodyLength,omitempty"`
	BinaryResponse bool           `json:"-"`
	URL            string         `json:"url,omitempty"`
	Redirected     bool           `json:"redirected"`
	Error          *responseError `json:"error,omitempty"`
}

type responseError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func errorResponse(id, code, message string) responseMessage {
	return responseMessage{
		ID: id,
		Error: &responseError{
			Code:    code,
			Message: message,
		},
	}
}

func main() {
	if err := serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "edge transport pipe failed")
		os.Exit(1)
	}
}

func serve(input io.Reader, output io.Writer) (serveErr error) {
	engine := newEngine()
	defer engine.close()
	serveCtx, stop := context.WithCancel(context.Background())
	defer stop()

	var outputMu sync.Mutex
	var outputErr error
	writeBytes := func(data []byte) error {
		written, err := output.Write(data)
		if err == nil && written != len(data) {
			return io.ErrShortWrite
		}
		return err
	}

	write := func(message responseMessage) {
		outputMu.Lock()
		defer outputMu.Unlock()

		if outputErr != nil {
			return
		}

		var body []byte
		if message.BinaryResponse {
			body = message.Body
			length := len(body)
			message.BodyLength = &length
			message.Body = nil
		}

		// Keep metadata and its exact-length binary body together on the pipe.
		var metadata []byte
		metadata, outputErr = json.Marshal(message)
		if outputErr == nil {
			outputErr = writeBytes(append(metadata, '\n'))
		}
		if outputErr == nil && len(body) > 0 {
			outputErr = writeBytes(body)
		}
		if outputErr != nil {
			stop()
			if closer, ok := input.(io.Closer); ok {
				_ = closer.Close()
			}
		}
	}

	var activeMu sync.Mutex
	active := map[string]context.CancelFunc{}
	var workers sync.WaitGroup
	slots := make(chan struct{}, 32)

	defer func() {
		activeMu.Lock()

		for _, cancel := range active {
			cancel()
		}

		activeMu.Unlock()
		workers.Wait()
		if outputErr != nil {
			serveErr = outputErr
		}
	}()

	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 65536), maxFrame)

	for scanner.Scan() {
		var request requestMessage

		if json.Unmarshal(scanner.Bytes(), &request) != nil || request.ID == "" || len(request.ID) > 256 {
			write(errorResponse(request.ID, "INVALID_REQUEST", "Invalid transport message"))
			continue
		}

		if request.Type == "cancel" {
			activeMu.Lock()

			if cancel := active[request.ID]; cancel != nil {
				cancel()
			}

			activeMu.Unlock()
			continue
		}

		if request.Type != "request" {
			write(errorResponse(request.ID, "INVALID_REQUEST", "Unknown transport message type"))
			continue
		}

		ctx, cancel := context.WithCancel(serveCtx)
		activeMu.Lock()

		if len(active) >= 128 {
			activeMu.Unlock()
			cancel()
			write(errorResponse(request.ID, "BUSY_ERR", "Too many pending requests"))
			continue
		}

		if _, exists := active[request.ID]; exists {
			activeMu.Unlock()
			cancel()
			write(errorResponse(request.ID, "INVALID_REQUEST", "Duplicate request ID"))
			continue
		}

		active[request.ID] = cancel
		activeMu.Unlock()
		workers.Add(1)

		go func(request requestMessage) {
			defer workers.Done()
			defer func() {
				cancel()
				activeMu.Lock()
				delete(active, request.ID)
				activeMu.Unlock()
			}()

			select {
			case slots <- struct{}{}:
				defer func() {
					<-slots
				}()
			case <-ctx.Done():
				write(errorResponse(request.ID, "ABORT_ERR", "Request cancelled"))
				return
			}

			write(engine.execute(ctx, request))
		}(request)
	}

	return scanner.Err()
}
