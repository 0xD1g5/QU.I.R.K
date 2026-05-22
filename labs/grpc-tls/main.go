// Minimal gRPC TLS server for the chaos lab (Phase 89 / LAB-05).
//
// grpc-go automatically sets NextProtos: ["h2"] when TLS credentials are used,
// so this server advertises ALPN h2 on :443. The cert is a self-signed RSA-2048
// (quantum-vulnerable MEDIUM finding expected by the scanner).
package main

import (
	"log"
	"net"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

// server implements the health-check echo used to keep the container alive.
// No real service is registered — the scanner probes TLS at the transport layer.
type server struct{}

func main() {
	creds, err := credentials.NewServerTLSFromFile("/tls/server.crt", "/tls/server.key")
	if err != nil {
		log.Fatalf("failed to load TLS credentials: %v", err)
	}

	// grpc-go automatically negotiates ALPN "h2" when TLS credentials are set.
	s := grpc.NewServer(grpc.Creds(creds))

	lis, err := net.Listen("tcp", ":443")
	if err != nil {
		log.Fatalf("failed to listen on :443: %v", err)
	}

	log.Printf("grpc-tls server listening on :443 (ALPN h2, RSA-2048 cert)")
	if err := s.Serve(lis); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}
