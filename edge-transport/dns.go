package main

import (
	"bytes"
	"context"
	"errors"
	"io"
	"net"
	stdhttp "net/http"
	"net/url"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/miekg/dns"
)

type echEntry struct {
	config  []byte
	expires time.Time
}

type echResolver struct {
	mu     sync.Mutex
	cache  map[string]echEntry
	doh    string
	client *stdhttp.Client
}

func (r *echResolver) remember(host string, config []byte, ttl time.Duration) {
	r.mu.Lock()
	defer r.mu.Unlock()

	r.cache[host] = echEntry{
		config:  append([]byte(nil), config...),
		expires: time.Now().Add(ttl),
	}
}

func newECHResolver(doh string) (*echResolver, error) {
	if doh != "" {
		u, err := url.Parse(doh)
		if err != nil || u.Scheme != "https" || u.Hostname() == "" || u.User != nil {
			return nil, errors.New("DoH resolver must be an HTTPS URL without credentials")
		}
	}

	return &echResolver{
		cache:  map[string]echEntry{},
		doh:    doh,
		client: &stdhttp.Client{Timeout: 5 * time.Second},
	}, nil
}

// HTTPS records use the user's OS DNS servers unless an explicit DoH endpoint
// is configured. DNS failures leave ECH unavailable; advertised ECH is never
// silently disabled after a TLS failure.
func (r *echResolver) lookup(ctx context.Context, host string) []byte {
	if net.ParseIP(host) != nil {
		return nil
	}

	r.mu.Lock()
	entry, ok := r.cache[host]
	r.mu.Unlock()

	if ok && time.Now().Before(entry.expires) {
		return entry.config
	}

	lookupCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	config, ttl := r.query(lookupCtx, dns.Fqdn(host), 0)
	if ttl <= 0 {
		ttl = 30 * time.Second
	}

	if ttl > time.Hour {
		ttl = time.Hour
	}

	r.mu.Lock()

	// Bound cache growth for a long-lived desktop process.
	if len(r.cache) >= 512 {
		r.cache = map[string]echEntry{}
	}

	r.cache[host] = echEntry{config: config, expires: time.Now().Add(ttl)}
	r.mu.Unlock()

	return config
}

func (r *echResolver) exchange(ctx context.Context, question *dns.Msg) (*dns.Msg, error) {
	if r.doh != "" {
		wire, err := question.Pack()
		if err != nil {
			return nil, err
		}

		req, err := stdhttp.NewRequestWithContext(ctx, "POST", r.doh, bytes.NewReader(wire))
		if err != nil {
			return nil, err
		}

		req.Header.Set("Content-Type", "application/dns-message")
		req.Header.Set("Accept", "application/dns-message")

		response, err := r.client.Do(req)
		if err != nil {
			return nil, err
		}

		defer response.Body.Close()

		if response.StatusCode != 200 {
			return nil, errors.New("DoH lookup failed")
		}

		wire, err = io.ReadAll(io.LimitReader(response.Body, 65536))
		if err != nil {
			return nil, err
		}

		answer := new(dns.Msg)
		if err = answer.Unpack(wire); err != nil {
			return nil, err
		}

		if answer.Id != question.Id {
			return nil, errors.New("DNS response mismatch")
		}

		return answer, nil
	}

	for _, server := range systemDNSServers() {
		client := &dns.Client{Timeout: 1500 * time.Millisecond}
		answer, _, err := client.ExchangeContext(ctx, question, server)
		if err != nil {
			continue
		}

		if answer.Truncated {
			client.Net = "tcp"
			answer, _, err = client.ExchangeContext(ctx, question, server)
		}

		if err == nil {
			return answer, nil
		}
	}

	return nil, errors.New("HTTPS DNS lookup unavailable")
}

func (r *echResolver) query(ctx context.Context, name string, depth int) ([]byte, time.Duration) {
	if depth >= 5 {
		return nil, 0
	}

	question := new(dns.Msg)
	question.SetQuestion(name, dns.TypeHTTPS)
	question.SetEdns0(1232, false)

	answer, err := r.exchange(ctx, question)
	if err != nil || answer.Rcode != dns.RcodeSuccess {
		return nil, 0
	}

	var records []*dns.HTTPS

	for _, record := range answer.Answer {
		switch value := record.(type) {
		case *dns.HTTPS:
			records = append(records, value)
		case *dns.CNAME:
			if strings.EqualFold(value.Hdr.Name, name) {
				return r.query(ctx, value.Target, depth+1)
			}
		}
	}

	sort.SliceStable(records, func(i, j int) bool {
		return records[i].Priority < records[j].Priority
	})

	for _, record := range records {
		if record.Priority == 0 && record.Target != "." {
			return r.query(ctx, record.Target, depth+1)
		}

		for _, param := range record.Value {
			if ech, ok := param.(*dns.SVCBECHConfig); ok && len(ech.ECH) > 0 {
				return append([]byte(nil), ech.ECH...), time.Duration(record.Hdr.Ttl) * time.Second
			}
		}
	}

	return nil, 30 * time.Second
}
