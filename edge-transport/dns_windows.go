//go:build windows

package main

import (
	"net"
	"unsafe"

	"golang.org/x/sys/windows"
)

func systemDNSServers() []string {
	var size uint32 = 15000

	for attempts := 0; attempts < 3; attempts++ {
		buf := make([]byte, size)
		first := (*windows.IpAdapterAddresses)(unsafe.Pointer(&buf[0]))
		err := windows.GetAdaptersAddresses(windows.AF_UNSPEC, windows.GAA_FLAG_SKIP_ANYCAST|windows.GAA_FLAG_SKIP_MULTICAST, 0, first, &size)
		if err == windows.ERROR_BUFFER_OVERFLOW {
			continue
		}

		if err != nil {
			return nil
		}

		seen := map[string]bool{}
		var servers []string

		for adapter := first; adapter != nil; adapter = adapter.Next {
			if adapter.OperStatus != windows.IfOperStatusUp {
				continue
			}

			for address := adapter.FirstDnsServerAddress; address != nil; address = address.Next {
				ip := address.Address.IP()
				if ip == nil || ip.IsUnspecified() {
					continue
				}

				server := net.JoinHostPort(ip.String(), "53")
				if !seen[server] {
					seen[server] = true
					servers = append(servers, server)
				}
			}
		}

		return servers
	}

	return nil
}
