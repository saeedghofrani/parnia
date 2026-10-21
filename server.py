"""Start the local Parnia studio over HTTP or HTTPS."""

import argparse
import os
from pathlib import Path
import ssl

from parnia_web import app


def local_tls(folder):
    import trustme
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cert, key, ca_path = folder / "server.pem", folder / "server.key", folder / "ca.pem"
    if not all(path.exists() for path in (cert, key, ca_path)):
        ca = trustme.CA()
        certificate = ca.issue_cert("localhost", "127.0.0.1", "::1")
        ca.cert_pem.write_to_path(ca_path)
        certificate.private_key_pem.write_to_path(key)
        certificate.cert_chain_pems[0].write_to_path(cert)
        key.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    return context


def main():
    cli = argparse.ArgumentParser(description="Run Parnia's local web studio.")
    cli.add_argument("--https", action="store_true", help="Local TLS on https://localhost:8443")
    cli.add_argument("--host", default="127.0.0.1")
    cli.add_argument("--port", type=int)
    cli.add_argument("--cert", help="Your own PEM certificate (requires --key)")
    cli.add_argument("--key", help="Your own PEM private key (requires --cert)")
    args = cli.parse_args()
    if bool(args.cert) != bool(args.key):
        cli.error("Use --cert and --key together.")
    port = args.port or int(os.environ.get("PORT", "8443" if args.https or args.cert else "8000"))
    if not 1 <= port <= 65535:
        cli.error("Port must be from 1 to 65535.")
    if args.https or args.cert:
        if args.https and not args.cert and args.host not in ("localhost", "127.0.0.1", "::1"):
            cli.error("Generated HTTPS certificates are local-only. Use a real certificate for another host.")
        context = (args.cert, args.key) if args.cert else local_tls(Path(__file__).parent / ".local-tls")
        print(f"Parnia: https://localhost:{port}", flush=True)
        if not args.cert:
            print("Local development certificate: your browser may ask you to trust it.", flush=True)
        app.run(host=args.host, port=port, ssl_context=context, debug=False, use_reloader=False)
    else:
        from waitress import serve
        print(f"Parnia: http://{args.host}:{port}", flush=True)
        serve(app, host=args.host, port=port, threads=4, max_request_body_size=8*1024*1024)


if __name__ == "__main__":
    main()
