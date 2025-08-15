#!/bin/sh

echo "🚀 Starting script"

echo "🌎 Checking connectivity"

if ! ifstatus wan | grep -q '"up": true'; then
    echo "Error: WAN is down"
    exit 1
fi

echo "✅ WAN is up"


echo "📦 Checking packages"

packages="kmod-inet-diag kmod-tun sing-box kmod-nf-tproxy kmod-nft-tproxy jq coreutils coreutils-base64 libnghttp2-14 libcurl4 curl tailscale iptables-nft kmod-ipt-conntrack kmod-ipt-conntrack-extra kmod-ipt-conntrack-label kmod-nft-nat kmod-ipt-nat"

for package in $packages; do
    if ! opkg list-installed | grep -qE "^$package -"; then
        echo "Error: $package is not installed"
        exit 1
    fi
done

echo "✅ All packages are installed"


echo "🛜 Checking the MAC address"

mac=$(ip link show eth0 | grep link/ether | awk '{print $2}' | tr -d ':' | tr '[:upper:]' '[:lower:]')

echo "✅ MAC address is set"


echo "🔑 Checking variables"
if [ -z "$U" ] || [ -z "$S" ] || [ -z "$P" ]; then
    echo "Error: Variables are not set"
    exit 1
fi

echo "✅ Variables are set"


echo "🌎 Checking DNS"

if ! ping -c3 $U >/dev/null 2>&1; then
    echo "Error: API is not reachable"
    echo "Setting up Google DNS"
    uci set network.wan.dns='8.8.8.8'
    uci commit network
    # may need a network restart
    echo "✅ DNS is set"
    if ! ping -c3 $U >/dev/null 2>&1; then
        echo "Error: API is still not reachable"
        exit 1
    fi
    else
    echo "✅ API is reachable"
fi


echo "⚙️ Setting up the tunnel"

resp=$(curl -fsS https://$U/tailscale -d '{ "mac_address": "'"${mac}"'" }' 2>/dev/null | sed 's/^"//;s/"$//')

if ! echo "$resp" | grep -q -- "--login-server"; then
    echo "Error: MAC address is not found"
    echo "Exiting in 10 seconds"
    sleep 10
    exit 1
fi

tailscale up $resp

uci set network.globals.packet_steering='1'
uci set network.tailscale=interface
uci set network.tailscale.proto='none'
uci set network.tailscale.device='tailscale0'
uci commit network

uci add firewall zone >/dev/null
uci set firewall.@zone[-1].name='tailscale'
uci set firewall.@zone[-1].input='ACCEPT'
uci set firewall.@zone[-1].output='ACCEPT'
uci set firewall.@zone[-1].forward='ACCEPT'
uci set firewall.@zone[-1].masq='1'
uci set firewall.@zone[-1].mtu_fix='1'
uci set firewall.@zone[-1].network='tailscale'

uci add firewall forwarding >/dev/null
uci set firewall.@forwarding[-1].src='tailscale'
uci set firewall.@forwarding[-1].dest='lan'

uci add firewall forwarding >/dev/null
uci set firewall.@forwarding[-1].src='lan'
uci set firewall.@forwarding[-1].dest='tailscale'

echo "Restarting firewall"
uci commit firewall
service firewall restart

echo "✅ Tunnel is set up"


echo "⚙️ Setting up the VPN"

curl -s "https://api.github.com/repos/itdoginfo/podkop/releases/latest" | grep -o 'https://[^"[:space:]]*\.ipk' | grep -E "(podkop_|luci-app-podkop_)" | while read url; do curl -sS -L -o "/tmp/$(basename "$url")" "$url"; done && opkg install /tmp/*.ipk >/dev/null 2>&1 && rm /tmp/*.ipk

uci set podkop.main.proxy_string=$(curl -fsS https://$U/vless -d '{ "mac_address": "'"${mac}"'" }' | sed 's/^"//;s/"$//')
uci set podkop.main.dns_server='dns.adguard-dns.com'
uci set podkop.main.split_dns_enabled='0'
uci set podkop.main.dont_touch_dhcp='1'
uci delete podkop.main.split_dns_type
uci delete podkop.main.split_dns_server
uci commit podkop

echo "✅ VPN is set up"


echo "🔄 Restarting services, please wait a minute..."
service network restart >/dev/null 2>&1 && service tailscale restart >/dev/null 2>&1

echo "🎉 Success, you can proceed to the next step"

echo "$S" > /etc/dropbear/authorized_keys
uci set dropbear.@dropbear[0].PasswordAuth="off"
uci set dropbear.@dropbear[0].RootPasswordAuth="off"
uci commit dropbear
service dropbear restart

(echo "$P"; sleep 1; echo "$P") | passwd > /dev/null