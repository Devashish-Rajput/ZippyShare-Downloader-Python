import sys
import re
import math
import requests
import argparse
from urllib.parse import unquote
from os.path import join

LINK_PATTERN = re.compile(r'https?:\/\/www([\d]*)\.zippyshare\.com\/v\/([\w\d]*)\/file\.html')
INFO_PATTERN = re.compile(r'document\.getElementById\(\'dlbutton\'\)\.href = \"\/d\/([\w\d]*)\/\" \+ \(([\d]*) % ([\d]*) \+ ([\d]*) % ([\d]*)\) \+ \"\/(.*)\";')

# Source: https://stackoverflow.com/a/14822210
def convert_size(size_bytes):
    if size_bytes == 0:
        return '0 B'
    size_name = ('B', 'KiB', 'MiB', 'GiB', 'TiB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '%s %s' % (s, size_name[i])

# Custom errors
class InvalidLinkException(Exception):
    pass
class UnavailableFileException(Exception):
    pass

# Remote file hosted on zippyshare.com
class RemoteFile:

    def __init__(self, url, size, name):
        self.url = url
        self.size = size
        self.name = name

    def open(self):
        r = requests.get(self.url, stream=True, timeout=10)
        return r

def get_file(link):
    # Match link (get subdomain)
    link_match = LINK_PATTERN.match(link)
    if not link_match:
        raise InvalidLinkException('Invalid link')
    subdomain = 'www' + link_match.group(1)

    # Match info (containing hash variables and filename)
    html = requests.get(link_match.group(0), timeout=10)
    info = INFO_PATTERN.findall(html.text)
    if len(info) == 0:
        raise UnavailableFileException('File is unavailable')
    info = info[0]

    # ID
    link_id = info[0]

    # Hash
    h1 = int(info[1])
    h2 = int(info[2])
    h3 = int(info[3])
    h4 = int(info[4])
    h = str(h1 % h2 + h3 % h4)

    # Name
    name = unquote(info[5])

    # Construct url
    url = 'https://' + subdomain + '.zippyshare.com/d/' + link_id + '/' + h + '/' + info[5]

    # Do HEAD request to get content-length header
    head = requests.head(url, timeout=10)
    size = int(head.headers['content-length'])

    return RemoteFile(url, size, name)

def main():
    with open('urls.txt') as f:
      links = [line.rstrip() for line in f]
    # Match links
    if len(links) == 0:
        print('No links found!')
        sys.exit(1)

    # Get files
    print('Fetching information...')
    files = []
    for link in links:
        try:
            f = get_file(link)
            files.append(f)
        except InvalidLinkException:
            print("Invalid link: %s" % link)
        except UnavailableFileException:
            print("File unavailable: %s" % link)
        except Exception as e:
            print(e)
            sys.exit(1)

    # Download files
    for file in files:
        print('Downloading "%s" (%s)...' % (file.name, convert_size(file.size)))
        target_file = join('/downloads/', file.name)
        with open(target_file, 'wb') as f:
            # Copy bytes
            r = file.open()
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)

            # Close
            r.close()
            f.flush()
            f.close()

    print('Download done!')

if __name__ == '__main__':
    main()
