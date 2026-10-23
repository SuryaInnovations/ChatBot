"""
security/url_policy.py — Strict SSRF Protection and Domain Access Policy.

Ensures that outbound network requests (web search, browser automation, document fetching)
never contact local services, loopback, private RFC1918 subnets, cloud metadata services (169.254.169.254),
or blocked domains.
"""

import socket
import ipaddress
import urllib.parse
import logging
from typing import Tuple, Set, Optional

logger = logging.getLogger("chatbot.security.url_policy")

# Denied domain keywords and known malicious or internal targets
BLOCKED_HOSTNAMES: Set[str] = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "169.254.169.254", # AWS/GCP/Azure link-local metadata
    "instance-data",
    "local",
    "internal"
}

ALLOWED_SCHEMES: Set[str] = {"http", "https"}
ALLOWED_PORTS: Set[int] = {80, 443}


class URLPolicy:
    def __init__(
        self,
        allowed_schemes: Optional[Set[str]] = None,
        allowed_ports: Optional[Set[int]] = None,
        blocked_domains: Optional[Set[str]] = None
    ):
        self.allowed_schemes = allowed_schemes or ALLOWED_SCHEMES
        self.allowed_ports = allowed_ports or ALLOWED_PORTS
        self.blocked_domains = set(blocked_domains or BLOCKED_HOSTNAMES)

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Validates URL safety against SSRF and intranet exposure.
        Returns (is_safe, error_message).
        """
        if not url or not isinstance(url, str):
            return False, "Invalid or empty URL provided."

        url = url.strip()
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            return False, f"Failed to parse URL: {e}"

        if not parsed.scheme or parsed.scheme.lower() not in self.allowed_schemes:
            return False, f"Prohibited URL scheme '{parsed.scheme}'. Only {list(self.allowed_schemes)} are permitted."

        hostname = parsed.hostname
        if not hostname:
            return False, "URL does not contain a valid hostname."

        hostname_lower = hostname.lower()
        if hostname_lower in self.blocked_domains or any(hostname_lower.endswith("." + b) for b in self.blocked_domains):
            return False, f"Access to blocked or internal hostname '{hostname}' is denied."

        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        if port not in self.allowed_ports:
            return False, f"Access to port {port} is prohibited. Allowed ports: {list(self.allowed_ports)}."

        # IP Resolution and Private IP Inspection
        try:
            addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
            for entry in addr_info:
                ip_str = entry[4][0]
                ip = ipaddress.ip_address(ip_str)

                # RFC1918, Loopback, Link-Local, Multicast, Reserved
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_reserved
                    or ip.is_multicast
                    or ip.is_unspecified
                ):
                    logger.warning(f"[SSRF BLOCKED] Destination resolved to restricted IP: {ip_str} for host: {hostname}")
                    return False, f"SSRF Blocked: Destination IP {ip_str} belongs to a private or restricted network."

                # Cloud metadata IP explicit check
                if str(ip) == "169.254.169.254":
                    return False, "SSRF Blocked: Cloud instance metadata service access is forbidden."

                # IPv6 mapped check
                if isinstance(ip, ipaddress.IPv6Address):
                    if ip.ipv4_mapped and (ip.ipv4_mapped.is_private or ip.ipv4_mapped.is_loopback):
                        return False, "SSRF Blocked: IPv4-mapped IPv6 address is private."

        except socket.gaierror as e:
            logger.warning(f"DNS resolution failure for {hostname}: {e}")
            return False, f"DNS resolution failed for hostname '{hostname}'."
        except Exception as e:
            logger.error(f"Error checking IP for {hostname}: {e}")
            return False, f"Security check error: {str(e)}"

        return True, ""


# Singleton policy instance
default_url_policy = URLPolicy()

def is_safe_url(url: str) -> Tuple[bool, str]:
    """Helper function to quickly check URL safety."""
    return default_url_policy.validate_url(url)
