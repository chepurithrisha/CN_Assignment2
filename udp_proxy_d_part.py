import socket
import struct
import time
import sys
from scapy.all import DNS, DNSQR

PROXY_LISTEN = ('0.0.0.0', 53)
CUSTOM_SERVER = ('10.0.0.5', 65000)
OUTBOUND_DNS = ('8.8.8.8', 53)

global_seq_id = 0

def extract_domain_and_build_query(request):
    try:
        dns_packet = DNS(request)
        domain = dns_packet[DNSQR].qname.decode().strip('.')
        question_section = request[12:request.find(b'\x00', 12)+5]
        return domain, question_section
    except Exception:
        return None, None

def build_basic_a_reply(trans_id, question, ip):
    qname_end = question.find(b'\x00') + 1
    qname = question[:qname_end]
    qtype_qclass = question[qname_end:qname_end+4]
    header = trans_id + b'\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00'
    question_section = qname + qtype_qclass
    answer = b'\xc0\x0c' + b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'
    answer += socket.inet_aton(ip)
    return header + question_section + answer

def send_to_custom_server(domain):
    global global_seq_id
    global_seq_id = (global_seq_id + 1) % 100
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(CUSTOM_SERVER)
        current_hour = time.strftime("%H")
        seq_id_str = f"{global_seq_id:02d}"
        custom_header = f"{current_hour}0000{seq_id_str}".encode('utf-8')
        from scapy.all import DNS, DNSQR
        msg_data = custom_header + bytes(DNS(rd=1, qd=DNSQR(qname=domain)))
        msg_len = len(msg_data)
        msg_prefix = struct.pack('>I', msg_len)
        sock.sendall(msg_prefix + msg_data)
        result = sock.recv(1024)
        sock.close()
        ip = result.decode().strip()
        if ip.startswith("Error"):
            return None
        return ip
    except Exception:
        return None

def send_to_outbound_dns(request):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    sock.sendto(request, OUTBOUND_DNS)
    try:
        data, _ = sock.recvfrom(512)
        return data
    except socket.timeout:
        return None

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(PROXY_LISTEN)
    print(f"[*] DNS UDP proxy listening on {PROXY_LISTEN}...")
    while True:
        data, addr = sock.recvfrom(512)
        trans_id = data[0:2]
        domain, question = extract_domain_and_build_query(data)
        if not domain or not question:
            continue
        ip = send_to_custom_server(domain)
        if ip:
            reply = build_basic_a_reply(trans_id, question, ip)
        else:
            outbound_resp = send_to_outbound_dns(data)
            if outbound_resp:
                reply = outbound_resp
            else:
                continue
        sock.sendto(reply, addr)

if __name__ == "__main__":
    if not hasattr(socket, 'AF_INET'):
        print("Error: Need AF_INET sockets support")
        sys.exit(1)
    main()
