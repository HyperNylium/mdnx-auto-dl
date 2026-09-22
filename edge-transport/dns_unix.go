//go:build !windows

package main

import (
	"net"

	"github.com/miekg/dns"
)

func systemDNSServers() []string {
	config, err := dns.ClientConfigFromFile("/etc/resolv.conf")
	if err != nil {
		return nil
	}

	servers := make([]string, 0, len(config.Servers))

	for _, server := range config.Servers {
		servers = append(servers, net.JoinHostPort(server, config.Port))
	}

	return servers
}
