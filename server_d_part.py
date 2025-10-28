import dns.message
import dns.query
import dns.rdatatype
import socket
import struct
import threading
import time

ROOT_SERVERS = [
    '198.41.0.4',      # a.root-servers.net
    '199.9.14.201',    # b.root-servers.net
    '192.33.4.12',     # c.root-servers.net
    '199.7.91.13',     # d.root-servers.net
    '192.203.230.10',  # e.root-servers.net
]

LISTEN_ADDR = '0.0.0.0'
LISTEN_PORT = 65000

def iterative_resolve(domain):
    query = dns.message.make_query(domain, dns.rdatatype.A)
    current_nameservers = ROOT_SERVERS[:]
    step_type = "root"
    while True:
        responded = False
        for ns in current_nameservers:
            try:
                resp = dns.query.udp(query, ns, timeout=3)
                if resp.rcode() != 0:
                    continue
                if len(resp.answer) > 0:
                    for ans in resp.answer:
                        if ans.rdtype == dns.rdatatype.A:
                            for rr in ans.items:
                                return rr.address
                # Referral: get NS names
                new_ns_names = []
                for auth in resp.authority:
                    if auth.rdtype == dns.rdatatype.NS:
                        for item in auth.items:
                            new_ns_names.append(item.target.to_text())
                # Get A for NS
                new_ns_ips = []
                for ar in resp.additional:
                    if ar.rdtype == dns.rdatatype.A:
                        for rr in ar.items:
                            new_ns_ips.append(rr.address)
                if not new_ns_ips:
                    for ns_name in new_ns_names:
                        try:
                            ns_a_resp = dns.query.udp(
                                dns.message.make_query(ns_name, dns.rdatatype.A),
                                ROOT_SERVERS[0], timeout=3)
                            for ans in ns_a_resp.answer:
                                for rr in ans.items:
                                    new_ns_ips.append(rr.address)
                        except Exception:
                            pass
                responded = True
                if step_type == "root":
                    step_type = "tld"
                else:
                    step_type = "auth"
                current_nameservers = new_ns_ips
                break
            except Exception:
                continue
        if not responded:
            return None

def handle_client(conn, addr):
    try:
        # Read 4-byte length prefix
        length_bytes = conn.recv(4)
        if len(length_bytes) < 4:
            conn.close()
            return
        msg_len = struct.unpack('>I', length_bytes)[0]
        data = b''
        while len(data) < msg_len:
            chunk = conn.recv(msg_len - len(data))
            if not chunk:
                break
            data += chunk
        if len(data) != msg_len:
            conn.close()
            return
        # Skip 8-byte custom header and DNS query object
        # Extract domain from DNS query data starting at offset 8
        # Use dnspython to parse the message
        dns_data = data[8:]
        try:
            dns_msg = dns.message.from_wire(dns_data)
            domain = str(dns_msg.question[0].name).rstrip('.')
        except Exception:
            conn.sendall(b"Error: Invalid DNS query")
            conn.close()
            return
        ip = iterative_resolve(domain)
        if ip:
            conn.sendall(ip.encode('utf-8'))
        else:
            conn.sendall(b"Error: Not found")
    except Exception:
        conn.sendall(b"Error: Server error")
    finally:
        conn.close()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((LISTEN_ADDR, LISTEN_PORT))
    sock.listen(5)
    print(f"[*] Iterative DNS Resolver TCP server listening {LISTEN_ADDR}:{LISTEN_PORT}...")
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    main()
