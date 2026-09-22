package main

import (
	"context"
	"errors"
	"net"
	"time"

	http "github.com/bogdanfinn/fhttp"
	"github.com/bogdanfinn/fhttp/http2"
	tls "github.com/bogdanfinn/utls"
)

func newTransport(resolver *echResolver) (*http.Transport, error) {
	cache := tls.NewLRUClientSessionCache(128)
	transport := &http.Transport{
		DisableCompression:     true,
		MaxIdleConns:           64,
		MaxIdleConnsPerHost:    8,
		IdleConnTimeout:        90 * time.Second,
		MaxResponseHeaderBytes: 1 << 20,
		ForceAttemptHTTP2:      true,
	}

	transport.DialTLSContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
		host, _, err := net.SplitHostPort(addr)
		if err != nil {
			return nil, err
		}

		ech := resolver.lookup(ctx, host)

		for attempt := 0; attempt < 2; attempt++ {
			dialer := &net.Dialer{
				Timeout:   20 * time.Second,
				KeepAlive: 30 * time.Second,
			}

			raw, err := dialer.DialContext(ctx, network, addr)
			if err != nil {
				return nil, err
			}

			config := &tls.Config{
				ServerName:         host,
				MinVersion:         tls.VersionTLS12,
				MaxVersion:         tls.VersionTLS13,
				ClientSessionCache: cache,
				OmitEmptyPsk:       true,
			}

			if transport.TLSClientConfig != nil {
				config.RootCAs = transport.TLSClientConfig.RootCAs
			}

			if len(ech) > 0 {
				config.EncryptedClientHelloConfigList = ech
				config.MinVersion = tls.VersionTLS13
			}

			conn := tls.UClient(raw, config, tls.HelloCustom, false, false, true)
			spec := edge153Spec()

			if len(ech) > 0 {
				spec.TLSVersMin = tls.VersionTLS13
			}

			if err = conn.ApplyPreset(spec); err == nil {
				err = conn.HandshakeContext(ctx)
			}

			if err != nil {
				raw.Close()
				var rejected *tls.ECHRejectionError

				// uTLS validates the public-name certificate before returning this
				// rejection. Retry only authenticated replacement configs, once.
				if attempt == 0 && errors.As(err, &rejected) && len(rejected.RetryConfigList) > 0 {
					ech = append([]byte(nil), rejected.RetryConfigList...)
					continue
				}

				return nil, err
			}

			if attempt > 0 && conn.ConnectionState().ECHAccepted {
				resolver.remember(host, ech, time.Minute)
			}

			return conn.Conn, nil
		}

		return nil, errors.New("ECH retry failed")
	}

	h2, err := http2.ConfigureTransports(transport)
	if err != nil {
		return nil, err
	}

	// fhttp's HTTP/2 response decoder does not inherit this flag from transport.
	h2.DisableCompression = true

	h2.Settings = map[http2.SettingID]uint32{
		http2.SettingHeaderTableSize:   65536,
		http2.SettingEnablePush:        0,
		http2.SettingInitialWindowSize: 6291456,
		http2.SettingMaxHeaderListSize: 262144,
	}

	h2.SettingsOrder = []http2.SettingID{
		http2.SettingHeaderTableSize,
		http2.SettingEnablePush,
		http2.SettingInitialWindowSize,
		http2.SettingMaxHeaderListSize,
	}

	h2.PseudoHeaderOrder = []string{":method", ":authority", ":scheme", ":path"}
	h2.ConnectionFlow = 15663105

	return transport, nil
}
