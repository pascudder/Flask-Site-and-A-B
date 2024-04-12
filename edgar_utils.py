import netaddr
from bisect import bisect
import pandas as pd
import re

ips = pd.read_csv("ip2location.csv")

def lookup_region(ip):
    global ips
    idx = bisect(ips['high'],int(netaddr.IPAddress(re.sub('[a-z]','0', ip))))
    return ips['region'][idx]

class Filing:
    def __init__(self, html):
        self.html_content = html
        self.dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", html)
        match = re.search(r'SIC=(\d+)', html)
        if match:
            self.sic = int(match.group(1))
        else:
            self.sic = None
                
        addresses = []
        for addr_html in re.findall(r'<div class="mailer">([\s\S]+?)</div>', html):
            lines = []
            for line in re.findall(r'<span class="mailerAddress">([\s\S]*?)</span>', addr_html):
                lines.append(line.strip())
            addresses.append("\n".join(lines))
        self.addresses = [item for item in addresses if item != ""]


    def state(self):
        for address in self.addresses:
            match = re.search(r'([A-Z]{2}) \d{5}', address)
        if match == None:
            return None
        else:
            return match.group(1)
