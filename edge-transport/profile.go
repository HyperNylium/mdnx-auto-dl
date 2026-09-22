package main

import (
	"crypto/rand"

	tls "github.com/bogdanfinn/utls"
)

func edge153Spec() *tls.ClientHelloSpec {
	var seed [1]byte

	if _, err := rand.Read(seed[:]); err != nil {
		panic(err)
	}

	g := uint16(seed[0]&0xf0) | 0x0a
	g |= g << 8

	spec := &tls.ClientHelloSpec{
		TLSVersMin: tls.VersionTLS12,
		TLSVersMax: tls.VersionTLS13,
		CipherSuites: []uint16{
			tls.GREASE_PLACEHOLDER,
			0x1301, 0x1302, 0x1303,
			0xc02b, 0xc02f, 0xc02c, 0xc030,
			0xcca9, 0xcca8, 0xc013, 0xc014,
			0x009c, 0x009d, 0x002f, 0x0035,
		},
		CompressionMethods: []byte{0},
		Extensions: []tls.TLSExtension{
			&tls.UtlsGREASEExtension{},
			&tls.PSKKeyExchangeModesExtension{Modes: []uint8{tls.PskModeDHE}},
			&tls.SignatureAlgorithmsExtension{
				SupportedSignatureAlgorithms: []tls.SignatureScheme{
					tls.SignatureScheme(g),
					0x0904, 0x0905, 0x0906,
					0x0403, 0x0804, 0x0401,
					0x0503, 0x0805, 0x0501,
					0x0806, 0x0601,
				},
			},
			&tls.UtlsCompressCertExtension{Algorithms: []tls.CertCompressionAlgo{tls.CertCompressionBrotli}},
			&tls.KeyShareExtension{
				KeyShares: []tls.KeyShare{
					{Group: tls.CurveID(tls.GREASE_PLACEHOLDER), Data: []byte{0}},
					{Group: tls.X25519MLKEM768},
					{Group: tls.X25519},
				},
			},
			&tls.ALPNExtension{AlpnProtocols: []string{"h2", "http/1.1"}},
			tls.BoringGREASEECH(),
			&tls.RenegotiationInfoExtension{Renegotiation: tls.RenegotiateOnceAsClient},
			&tls.SNIExtension{},
			&tls.SupportedVersionsExtension{Versions: []uint16{tls.GREASE_PLACEHOLDER, tls.VersionTLS13, tls.VersionTLS12}},
			&tls.SessionTicketExtension{},
			&tls.StatusRequestExtension{},
			&tls.SupportedPointsExtension{SupportedPoints: []byte{0}},
			&tls.SupportedCurvesExtension{
				Curves: []tls.CurveID{
					tls.GREASE_PLACEHOLDER,
					tls.X25519MLKEM768,
					tls.X25519,
					tls.CurveP256,
					tls.CurveP384,
				},
			},
			&tls.ExtendedMasterSecretExtension{},
			&tls.ApplicationSettingsExtensionNew{SupportedProtocols: []string{"h2"}},
			&tls.SCTExtension{},
			&tls.UtlsGREASEExtension{},
			&tls.UtlsPreSharedKeyExtension{},
		},
	}

	spec.Extensions = tls.ShuffleChromeTLSExtensions(spec.Extensions)

	return spec
}
