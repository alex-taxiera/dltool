#Myrient HTTP-server addresses
MYRIENTHTTPADDR = 'https://myrient.erista.me/files/'

#Catalog URLs, to parse out the catalog in use from DAT
CATALOGURLS = {
    'https://www.no-intro.org': 'No-Intro',
    'http://redump.org/': 'Redump'
}

#Postfixes in DATs to strip away
DATPOSTFIXES = [
    ' (Retool)'
]

#Chunk sizes to download
CHUNKSIZE = 8192

#Headers to use in HTTP-requests
REQHEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
}
