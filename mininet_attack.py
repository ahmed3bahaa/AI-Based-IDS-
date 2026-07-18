#!/usr/bin/env python3
import argparse
import os
import subprocess
import ipaddress
from functools import partial

from mininet.net import Mininet
from mininet.topolib import TreeTopo
from mininet.node import OVSSwitch, RemoteController
from mininet.log import setLogLevel, info
from mininet.clean import cleanup


def hard_cleanup():
    try:
        cleanup()
    except Exception:
        pass
    try:
        subprocess.run(["mn", "-c"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def must_be_ip(s: str, name: str) -> str:
    try:
        ipaddress.ip_address(s)
        return s
    except Exception:
        raise SystemExit(f"[ERROR] {name} must be a valid IP, got: {s!r}\n"
                         f"Tip: do NOT write $ before the IP. Use: --{name} 192.168.x.x")


def run_http(host, esp_ip, n, path="/data", port=80, parallel=10, timeout_s=2):
    url = f"http://{esp_ip}:{port}{path}"
    info(f"\n[HTTP] {host.name} -> {url} x{n} (parallel={parallel})\n")
    cmd = (
        f'seq 1 {n} | xargs -n1 -P {parallel} -I{{}} '
        f'curl -s --connect-timeout 1 --max-time {timeout_s} "{url}" >/dev/null'
    )
    host.cmd(f"bash -lc '{cmd}'")


def run_tcp(host, esp_ip, port, n, parallel=10):
    info(f"\n[TCP] {host.name} -> {esp_ip}:{port} x{n} (parallel={parallel})\n")
    cmd = (
        f'seq 1 {n} | xargs -n1 -P {parallel} -I{{}} '
        f'bash -lc \'echo hello | nc -w 1 {esp_ip} {port} >/dev/null\''
    )
    host.cmd(f"bash -lc \"{cmd}\"")


def run_mqtt(host, broker_ip, topic, msg, n, qos=0, parallel=10):
    info(f"\n[MQTT] {host.name} -> broker {broker_ip}:1883 topic={topic} x{n} (parallel={parallel})\n")
    cmd = (
        f'seq 1 {n} | xargs -n1 -P {parallel} -I{{}} '
        f'mosquitto_pub -h {broker_ip} -t "{topic}" -m "{msg}" -q {qos} >/dev/null 2>&1 || true'
    )
    host.cmd(f"bash -lc '{cmd}'")


def ensure_nat_rules(nat, uplink: str):
    """
    Why this exists:
    - IP forwarding must be enabled or nat0 won't route 10.0.0.x -> LAN
    - MASQUERADE must exist or replies won't return to 10.0.0.x
    - FORWARD rules must allow traffic in/out
    - Using -C || -A avoids duplicating rules each run
    """
    inside_intf = nat.defaultIntf().name  

    info("\n*** Enabling IP forwarding (host/nat0)\n")
    nat.cmd("sysctl -w net.ipv4.ip_forward=1 >/dev/null")

    
    nat.cmd("sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null || true")
    nat.cmd(f"sysctl -w net.ipv4.conf.{uplink}.rp_filter=0 >/dev/null || true")
    nat.cmd(f"sysctl -w net.ipv4.conf.{inside_intf}.rp_filter=0 >/dev/null || true")

    info("\n*** Enforcing NAT iptables rules\n")
    
    nat.cmd(
        f"iptables -t nat -C POSTROUTING -s 10.0.0.0/8 -o {uplink} -j MASQUERADE "
        f"2>/dev/null || "
        f"iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o {uplink} -j MASQUERADE"
    )

   
    nat.cmd(
        f"iptables -C FORWARD -i {inside_intf} -o {uplink} -j ACCEPT "
        f"2>/dev/null || "
        f"iptables -A FORWARD -i {inside_intf} -o {uplink} -j ACCEPT"
    )

   
    nat.cmd(
        f"iptables -C FORWARD -i {uplink} -o {inside_intf} -m state --state RELATED,ESTABLISHED -j ACCEPT "
        f"2>/dev/null || "
        f"iptables -A FORWARD -i {uplink} -o {inside_intf} -m state --state RELATED,ESTABLISHED -j ACCEPT"
    )


def fix_default_routes(hosts):
    """
    Why: hosts must know to send everything via nat0 (10.0.0.4)
    """
    info("\n*** Fixing default routes on Mininet hosts\n")
    for h in hosts:
        h.cmd("ip route del default >/dev/null 2>&1 || true")
        h.cmd("ip route add default via 10.0.0.4")


def main():
    if os.geteuid() != 0:
        print("Run this script with sudo.")
        raise SystemExit(1)

    p = argparse.ArgumentParser()
    p.add_argument("--esp", required=True, help="ESP32 IP (victim), e.g. 192.168.151.210")
    p.add_argument("--broker", required=True, help="MQTT broker IP (Ubuntu), e.g. 192.168.150.137")
    p.add_argument("--tcp-port", type=int, default=9000)

    p.add_argument("--http-n", type=int, default=200)
    p.add_argument("--tcp-n", type=int, default=200)
    p.add_argument("--mqtt-n", type=int, default=400)

    p.add_argument("--http-port", type=int, default=80)
    p.add_argument("--http-path", default="/data")

    p.add_argument("--mqtt-topic", default="esp32/cmd")
    p.add_argument("--mqtt-msg", default="ping")
    p.add_argument("--mqtt-qos", type=int, default=0)

    p.add_argument("--controller-ip", default=None)
    p.add_argument("--controller-port", type=int, default=6653)

    p.add_argument("--uplink", default="enp0s3", help="VM uplink interface to LAN (default: enp0s3)")
    p.add_argument("--warmup", type=int, default=3)
    p.add_argument("--parallel", type=int, default=10)
    args = p.parse_args()

    
    args.esp = must_be_ip(args.esp, "esp")
    args.broker = must_be_ip(args.broker, "broker")

    hard_cleanup()

    topo = TreeTopo(depth=1, fanout=3)

    if args.controller_ip:
        sw = partial(OVSSwitch, failMode="secure")
        net = Mininet(topo=topo, controller=None, switch=sw, autoSetMacs=True, autoStaticArp=True)
        net.addController("c0", controller=RemoteController, ip=args.controller_ip, port=args.controller_port)
        info(f"\n*** Using remote controller {args.controller_ip}:{args.controller_port}\n")
    else:
        sw = partial(OVSSwitch, failMode="standalone")
        net = Mininet(topo=topo, controller=None, switch=sw, autoSetMacs=True, autoStaticArp=True)
        info("\n*** No controller: OVS failMode=standalone (L2 forwarding enabled)\n")

    
    s1 = net.get("s1")
    nat = net.addNAT(name="nat0", connect=s1, ip="10.0.0.4/8")
    nat.configDefault(localIntf=args.uplink)

    info("\n*** Starting network\n")
    net.start()

    try:
        h1, h2, h3 = net.get("h1"), net.get("h2"), net.get("h3")

       
        ensure_nat_rules(nat, args.uplink)
        fix_default_routes([h1, h2, h3])

        info("\n*** Quick checks\n")
        info(h1.cmd("ip route") + "\n")
        info(h1.cmd("ping -c 2 10.0.0.4 || true") + "\n")

       
        info(h1.cmd(f"ping -c 2 {args.esp} || true") + "\n")
        info(h1.cmd(f"curl -m 2 -s -o /dev/null -w 'HTTP=%{{http_code}}\\n' http://{args.esp}:{args.http_port}{args.http_path} || true") + "\n")

        if args.warmup > 0:
            info(f"\n*** Warmup {args.warmup}s\n")
            h1.cmd(f"sleep {args.warmup}")

        for h, tool in [(h1, "curl"), (h2, "nc"), (h3, "mosquitto_pub")]:
            out = h.cmd(f"bash -lc 'command -v {tool} >/dev/null && echo OK || echo MISSING'")
            info(f"{h.name}: {tool} = {out.strip()}\n")

        run_http(h1, args.esp, args.http_n, path=args.http_path, port=args.http_port, parallel=args.parallel)
        run_tcp(h2, args.esp, args.tcp_port, args.tcp_n, parallel=args.parallel)
        run_mqtt(h3, args.broker, args.mqtt_topic, args.mqtt_msg, args.mqtt_n, qos=args.mqtt_qos, parallel=args.parallel)

        info("\n*** Done.\n")

    finally:
        info("\n*** Stopping network + cleanup\n")
        try:
            net.stop()
        finally:
            hard_cleanup()


if __name__ == "__main__":
    setLogLevel("info")
    main()

