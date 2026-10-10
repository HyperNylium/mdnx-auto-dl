package main

import (
	"bufio"
	"context"
	stdtls "crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/binary"
	"errors"
	"io"
	"net"
	stdhttp "net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	http "github.com/bogdanfinn/fhttp"
	"github.com/bogdanfinn/fhttp/http2"
	tls "github.com/bogdanfinn/utls"
	"golang.org/x/net/proxy"
)

func newTransport(resolver *echResolver, rawProxy string) (*http.Transport, error) {
	var proxyURL *url.URL
	if rawProxy != "" {
		parsed, err := url.Parse(rawProxy)
		if err != nil || parsed.Hostname() == "" || parsed.RawQuery != "" || parsed.Fragment != "" || (parsed.Path != "" && parsed.Path != "/") {
			return nil, errors.New("Invalid proxy URL")
		}
		switch parsed.Scheme {
		case "http", "https", "socks", "socks4", "socks4a", "socks5", "socks5h":
		default:
			return nil, errors.New("Unsupported proxy protocol")
		}
		if parsed.Port() != "" {
			port, err := strconv.Atoi(parsed.Port())
			if err != nil || port < 1 || port > 65535 {
				return nil, errors.New("Invalid proxy port")
			}
		}
		proxyURL = parsed
	}

	cache := tls.NewLRUClientSessionCache(128)
	transport := &http.Transport{
		DisableCompression:     true,
		MaxIdleConns:           64,
		MaxIdleConnsPerHost:    8,
		IdleConnTimeout:        90 * time.Second,
		MaxResponseHeaderBytes: 1 << 20,
		ForceAttemptHTTP2:      true,
	}
	dial := func(ctx context.Context, network, addr string) (net.Conn, error) {
		var roots *x509.CertPool
		if transport.TLSClientConfig != nil {
			roots = transport.TLSClientConfig.RootCAs
		}
		return dialProxy(ctx, network, addr, proxyURL, roots)
	}
	transport.DialContext = dial
	if proxyURL != nil && resolver.doh != "" {
		resolver.client.Transport = &stdhttp.Transport{DialContext: dial, DisableKeepAlives: true}
	}

	transport.DialTLSContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
		host, _, err := net.SplitHostPort(addr)
		if err != nil {
			return nil, err
		}

		ech := resolver.lookup(ctx, host)

		for attempt := 0; attempt < 2; attempt++ {
			raw, err := dial(ctx, network, addr)
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

// Tunnel before the target TLS handshake so proxy requests keep the same Edge profile.
func dialProxy(ctx context.Context, network, addr string, proxyURL *url.URL, roots *x509.CertPool) (conn net.Conn, err error) {
	dialer := &net.Dialer{Timeout: 20 * time.Second, KeepAlive: 30 * time.Second}
	if proxyURL == nil {
		return dialer.DialContext(ctx, network, addr)
	}

	ctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()
	host, portText, err := net.SplitHostPort(addr)
	if err != nil {
		return nil, errors.New("Invalid proxy target")
	}
	port, err := strconv.Atoi(portText)
	if err != nil || port < 1 || port > 65535 {
		return nil, errors.New("Invalid proxy target port")
	}
	proxyPort := proxyURL.Port()
	if proxyPort == "" {
		switch proxyURL.Scheme {
		case "http":
			proxyPort = "80"
		case "https":
			proxyPort = "443"
		default:
			proxyPort = "1080"
		}
	}
	proxyAddr := net.JoinHostPort(proxyURL.Hostname(), proxyPort)

	if proxyURL.Scheme == "socks5" || proxyURL.Scheme == "socks5h" || proxyURL.Scheme == "socks" {
		if proxyURL.Scheme == "socks5" && net.ParseIP(host) == nil {
			addresses, lookupErr := net.DefaultResolver.LookupIPAddr(ctx, host)
			if lookupErr != nil || len(addresses) == 0 {
				return nil, errors.New("SOCKS5 target DNS lookup failed")
			}
			addr = net.JoinHostPort(addresses[0].IP.String(), portText)
		}
		var auth *proxy.Auth
		if proxyURL.User != nil {
			password, _ := proxyURL.User.Password()
			auth = &proxy.Auth{User: proxyURL.User.Username(), Password: password}
		}
		socks, dialErr := proxy.SOCKS5("tcp", proxyAddr, auth, dialer)
		if dialErr != nil {
			return nil, errors.New("Invalid SOCKS5 configuration")
		}
		return socks.(proxy.ContextDialer).DialContext(ctx, network, addr)
	}

	raw, err := dialer.DialContext(ctx, network, proxyAddr)
	if err != nil {
		return nil, err
	}
	conn = raw
	deadline, _ := ctx.Deadline()
	_ = raw.SetDeadline(deadline)
	stop := context.AfterFunc(ctx, func() { raw.Close() })
	defer func() {
		stop()
		if err != nil {
			raw.Close()
		} else {
			_ = raw.SetDeadline(time.Time{})
		}
	}()

	if proxyURL.Scheme == "socks4" || proxyURL.Scheme == "socks4a" {
		ip := net.ParseIP(host)
		remoteDNS := proxyURL.Scheme == "socks4a" && ip == nil
		if !remoteDNS && ip == nil {
			addresses, lookupErr := net.DefaultResolver.LookupIP(ctx, "ip4", host)
			if lookupErr != nil || len(addresses) == 0 {
				return nil, errors.New("SOCKS4 target DNS lookup failed")
			}
			ip = addresses[0]
		}
		if remoteDNS {
			ip = net.IPv4(0, 0, 0, 1)
		}
		if ip.To4() == nil {
			return nil, errors.New("SOCKS4 requires an IPv4 target")
		}
		username := ""
		if proxyURL.User != nil {
			username = proxyURL.User.Username()
		}
		if len(username) > 255 || strings.ContainsRune(username, 0) || len(host) > 255 || strings.ContainsRune(host, 0) {
			return nil, errors.New("Invalid SOCKS4 target or username")
		}
		request := []byte{4, 1, 0, 0}
		binary.BigEndian.PutUint16(request[2:], uint16(port))
		request = append(request, ip.To4()...)
		request = append(request, username...)
		request = append(request, 0)
		if remoteDNS {
			request = append(request, host...)
			request = append(request, 0)
		}
		if _, err = conn.Write(request); err != nil {
			return nil, err
		}
		response := make([]byte, 8)
		if _, err = io.ReadFull(conn, response); err != nil {
			return nil, err
		}
		if response[0] != 0 || response[1] != 90 {
			return nil, errors.New("SOCKS4 proxy rejected the connection")
		}
		return conn, nil
	}

	if proxyURL.Scheme == "https" {
		tlsConn := stdtls.Client(raw, &stdtls.Config{ServerName: proxyURL.Hostname(), MinVersion: stdtls.VersionTLS12, RootCAs: roots})
		if err = tlsConn.HandshakeContext(ctx); err != nil {
			return nil, err
		}
		conn = tlsConn
	}
	request := &stdhttp.Request{Method: "CONNECT", URL: &url.URL{Opaque: addr}, Host: addr, Header: make(stdhttp.Header)}
	if proxyURL.User != nil {
		password, _ := proxyURL.User.Password()
		auth := base64.StdEncoding.EncodeToString([]byte(proxyURL.User.Username() + ":" + password))
		request.Header.Set("Proxy-Authorization", "Basic "+auth)
	}
	if err = request.Write(conn); err != nil {
		return nil, err
	}
	response, err := stdhttp.ReadResponse(bufio.NewReader(io.LimitReader(conn, 1<<20)), request)
	if err != nil {
		return nil, err
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, errors.New("HTTP proxy rejected the connection")
	}
	return conn, nil
}
