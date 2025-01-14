import sys
import socket
import urllib.request
from urllib.request import HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import subprocess
import re
import time
import os
from urllib.parse import urlparse
import pdb

#=================================================
# MAIN FUNCTION
#=================================================

def main():
    import argparse
    usage = "%prog [options]\n\n%prog - Tim Tomes (@LaNMaSteR53) (www.lanmaster53.com)"
    parser = argparse.ArgumentParser(description='Peepingtom Script', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', help='Enable verbose mode.', dest='verbose', default=False, action='store_true')
    parser.add_argument('-i', help='File input mode. Name of input file. [IP:PORT]', dest='infile', type=str, action='store')
    parser.add_argument('-u', help='Single URL input mode. URL as a string.', dest='url', type=str, action='store')
    parser.add_argument('-q', help='PyQt4 capture mode. PyQt4 python modules required.', dest='pyqt', default=False, action='store_true')
    parser.add_argument('-p', help='Phantonjs capture mode. Phantomjs required.', dest='phantom', default=False, action='store_true')
    args = parser.parse_args()

    if not args.infile and not args.url:
        parser.error("[!] Must provide input. Mode option required.")
    if not args.pyqt and not args.phantom:
        capture = False
        print('[!] WARNING: No capture mode provided. Retrieving header data only.')
    else:
        capture = True
    if args.infile:
        targets = open(args.infile).read().split()
    if args.url:
        targets = []
        targets.append(args.url)

    dir = time.strftime('%y%m%d_%H%M%S', time.localtime())
    print('[*] Storing data in \'%s/\'' % (dir))
    os.mkdir(dir)
    outfile = '%s/report.html' % (dir)
    
    socket.setdefaulttimeout(5)

    zombies = []
    servers = {}
    # logic for validating list of urls and building a new list which understands the redirected sites.
    try:
        for target in targets:
            headers = None
            prefix = ''
            # best guess at protocol prefix
            if not target.startswith('http'):
                if target.find(':') == -1: target += ':80'
                prefix = 'http://'
                if target.split(':')[1].find('443') != -1:
                    prefix = 'https://'
            # drop port suffix where not needed
            if target.endswith(':80'): target = ':'.join(target.split(':')[:-1])
            if target.endswith(':443'): target = ':'.join(target.split(':')[:-1])
            # build legitimate target url
            target = prefix + target
            code, headers = getHeaderData(target)
            if code == 'zombie':
                zombies.append((target, headers))
            else:
                filename = '%s.png' % re.sub(r'\W','',target)
                servers[target] = [code, filename, headers]
                if capture: getCapture(code, target, '%s/%s' % (dir,filename), args)
    except KeyboardInterrupt:
        print('Interrupted by keyboard.')  # Properly indented

    
    generatePage(servers, zombies, outfile)
    print('Done.')

#=================================================
# SUPPORT FUNCTIONS
#=================================================

def getCapture(code, url, filename, opts):
    if code != 401:
        verbose = opts.verbose
        try:
            if opts.pyqt:      cmd = 'python ./capture.py %s %s' % (url, filename)
            elif opts.phantom: cmd = './phantomjs --ignore-ssl-errors=yes ./screenshot.js %s %s' % (url, filename)
            else: return
            proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            stdout, stderr = proc.communicate()
            response = str(stdout) + str(stderr)
            returncode = proc.returncode
            if returncode != 0:
                print('[!] %d: %s' % (returncode, response))
            if response != 'None':
                if verbose: print('[+] \'%s\' => %s' % (cmd, repr(response)))
        except KeyboardInterrupt:
            pass

def getHeaderData(target):
    server = None
    url = None
    code = None
    status = None
    headers = None
    header_str = None
    server = urlparse(target)
    opener = urllib.request.build_opener(SmartRedirectHandler)  # debug with urllib.request.HTTPHandler(debuglevel=1)
    urllib.request.install_opener(opener)

    req = urllib.request.Request(server.geturl())

    try:
        res = urllib.request.urlopen(req)
        print('[*] %s %s. Good.' % (target, res.getcode()))
    except HTTPError as e:
        print('[*] %s %s. Visit manually from report.' % (target, e.code))
        return 'zombie', e.reason
    except URLError as e:
        print('[*] %s. Error: %s' % (target, e.reason))
        return 'zombie', e.reason
    except Exception as e:
        print('[*] %s %s. Visit manually from report.' % (target, str(e)))
        return 'zombie', str(e)

    url = res.geturl()
    code = res.code
    status = res.msg   
    headers = list(res.headers.items()) 
    header_str = '<br />%s %s<br />\n' % (code, status)
    for header in headers:
        header_str += '<span class="header">%s</span>: %s<br />\n' % (header[0], header[1])
    return code, header_str

def generatePage(servers, zombies, outfile):
    tmarkup = ''
    zmarkup = ''
    #pdb.set_trace()
    for server in sorted(servers.keys()):  #added sorting, easier to work having always right order
        tmarkup += "<tr>\n<td class='img'><img src='%s' /></td>\n<td class='head'><a href='%s' target='_blank'>%s</a> %s</td>\n</tr>\n" % (servers[server][1],server,server,servers[server][2])
    if len(zombies) > 0:
      zmarkup = '<tr><td><h2>Failed Requests</h2></td><td>\n'
      for server in sorted(zombies):  #sort as well
          zmarkup +=  "<a href='%s' target='_blank'>%s</a> %s<br />\n" % (server[0],server[0],server[1])
      zmarkup += '</td></tr>\n'
    file = open(outfile, 'w')
    file.write("""
<!doctype html>
<head>
<style>
table, td, th {border: 1px solid black;border-collapse: collapse;padding: 5px;font-size: .9em;font-family: tahoma;}
table {table-layout:fixed;}
td.img {width: 400px;white-space: nowrap;}
td.head {vertical-align: top;word-wrap:break-word;}
.header {font-weight: bold;}
img {width: 400px;}
</style>
</head>
<body>
<table width='100%%'>
%s%s
</table>
</body>
</html>""" % (tmarkup, zmarkup))
    file.close()

#=================================================
# CUSTOM CLASS WRAPPERS
#=================================================

class SmartRedirectHandler(HTTPRedirectHandler):

    def http_error_301(self, req, fp, code, msg, headers):
        result = super().http_error_301(req, fp, code, msg, headers)
        result.status = code
        result.msg = msg + ' (Redirect)'
        return result

    # Mapowanie innych kodów przekierowań na tę samą obsługę
    http_error_302 = http_error_303 = http_error_307 = http_error_301

#=================================================
# START
#=================================================

if __name__ == "__main__": main()

