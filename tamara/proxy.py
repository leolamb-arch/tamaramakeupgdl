"""Trust forwarding headers only from explicitly configured proxy networks."""

from ipaddress import ip_address, ip_network
from werkzeug.middleware.proxy_fix import ProxyFix


class TrustedProxy:
    def __init__(self, app, networks):
        self.app = app
        self.networks = [
            ip_network(item.strip()) for item in networks.split(",") if item.strip()
        ]
        self.forwarded = ProxyFix(
            app, x_for=1, x_proto=1, x_host=0, x_port=0, x_prefix=0
        )

    def __call__(self, environ, start_response):
        try:
            trusted = any(
                ip_address(environ.get("REMOTE_ADDR", "")) in network
                for network in self.networks
            )
        except ValueError:
            trusted = False
        return (self.forwarded if trusted else self.app)(environ, start_response)
