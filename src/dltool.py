import os
import re
import signal
import argparse
import platform
import requests
import textwrap
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from src.const import CATALOGURLS, DATPOSTFIXES, MYRIENTHTTPADDR, REQHEADERS
from src.types import RomMeta
from src.utils import download, exithandler, inputter, logger

signal.signal(signal.SIGINT, exithandler)

#Generate argument parser
parser = argparse.ArgumentParser(
    add_help=False,
    formatter_class=argparse.RawTextHelpFormatter,
    description=textwrap.dedent('''\
        \033[92mTool to automatically download ROMs of a DAT-file from Myrient.
        
        Generate a DAT-file with the tool of your choice to include ROMs that you
        want from a No-Intro/Redump/etc catalog, then use this tool to download
        the matching files from Myrient.\033[00m
    '''))

#Add required arguments
requiredargs = parser.add_argument_group('\033[91mRequired arguments\033[00m')
requiredargs.add_argument('-i', dest='inp', metavar='nointro.dat', help='Input DAT-file containing wanted ROMs', required=True)
requiredargs.add_argument('-o', dest='out', metavar='/data/roms', help='Output path for ROM files to be downloaded', required=True)
#Add optional arguments
optionalargs = parser.add_argument_group('\033[96mOptional arguments\033[00m')
optionalargs.add_argument('-c', dest='catalog', action='store_true', help='Choose catalog manually, even if automatically found')
optionalargs.add_argument('-s', dest='system', action='store_true', help='Choose system collection manually, even if automatically found')
optionalargs.add_argument('-l', dest='list', action='store_true', help='List only ROMs that are not found in server (if any)')
optionalargs.add_argument('-h', '--help', dest='help', action='help', help='Show this help message')
args = parser.parse_args()

#Init variables
catalog = None
collection = None
wantedroms: list[str] = []
wantedfiles: list[RomMeta] = []
missingroms: list[str] = []
availableroms: dict[str, RomMeta] = {}
foundcollections = []

#Validate arguments
if not os.path.isfile(args.inp):
    logger('Invalid input DAT-file!', 'red')
    exit()
if not os.path.isdir(args.out):
    logger('Invalid output ROM path!', 'red')
    exit()
if platform.system() == 'Linux' and args.out[-1] == '/':
    args.out = args.out[:-1]
elif platform.system() == 'Windows' and args.out[-1] == '\\':
    args.out = args.out[:-1]

#Open input DAT-file
logger('Opening input DAT-file...', 'green')
datxml = ET.parse(args.inp)
datroot = datxml.getroot()

#Loop through ROMs in input DAT-file
for datchild in datroot:
    #Print out system information
    if datchild.tag == 'header':
        system = datchild.find('name').text
        for fix in DATPOSTFIXES:
            system = system.replace(fix, '')
        catalogurl = datchild.find('url').text
        if catalogurl in CATALOGURLS:
            catalog = CATALOGURLS[catalogurl]
            logger(f'Processing {catalog}: {system}...', 'green')
        else:
            logger(f'Processing {system}...', 'green')
    #Add found ROMs to wanted list
    elif datchild.tag == 'game':
        filename = datchild.attrib['name']
        filename = re.sub(r'\.[(a-zA-Z0-9)]{1,3}\Z', '', filename)
        if filename not in wantedroms:
            wantedroms.append(filename)

#Get HTTP base and select wanted catalog
catalogurl = None
resp = requests.get(MYRIENTHTTPADDR, headers=REQHEADERS).text
resp = BeautifulSoup(resp, 'html.parser')
maindir = resp.find('table', id='list').tbody.find_all('tr')
for dir in maindir[1:]:
    cell = dir.find('td')
    if catalog in cell.a['title']:
        catalogurl = cell.a['href']

if not catalogurl or args.catalog:
    logger('Catalog for DAT not automatically found, please select from the following:', 'yellow')
    dirnbr = 1
    catalogtemp = {}
    for dir in maindir[1:]:
        cell = dir.find('td')
        logger(f'{str(dirnbr).ljust(2)}: {cell.a["title"]}', 'yellow')
        catalogtemp[dirnbr] = {'name': cell.a['title'], 'url': cell.a['href']}
        dirnbr += 1
    while True:
        sel = inputter('Input selected catalog number: ', 'cyan')
        try:
            sel = int(sel)
            if sel > 0 and sel < dirnbr:
                catalog = catalogtemp[sel]['name']
                catalogurl = catalogtemp[sel]['url']
                break
            else:
                logger('Input number out of range!', 'red')
        except:
            logger('Invalid number!', 'red')

#Get catalog directory and select wanted collection
collectionurl = None
resp = requests.get(f'{MYRIENTHTTPADDR}{catalogurl}', headers=REQHEADERS).text
resp = BeautifulSoup(resp, 'html.parser')
contentdir = resp.find('table', id='list').tbody.find_all('tr')
for dir in contentdir[1:]:
    cell = dir.find('td')
    if cell.a['title'].startswith(system):
        foundcollections.append({'name': cell.a['title'], 'url': cell.a['href']})
if len(foundcollections) == 1:
    collection = foundcollections[0]['name']
    collectionurl = foundcollections[0]['url']
if not collection or args.system:
    logger('Collection for DAT not automatically found, please select from the following:', 'yellow')
    dirnbr = 1
    if len(foundcollections) > 1 and not args.system:
        for foundcollection in foundcollections:
            logger(f'{str(dirnbr).ljust(2)}: {foundcollection["name"]}', 'yellow')
            dirnbr += 1
    else:
        collectiontemp = {}
        for dir in contentdir[1:]:
            cell = dir.find('td')
            logger(f'{str(dirnbr).ljust(2)}: {cell.a["title"]}', 'yellow')
            collectiontemp[dirnbr] = {'name': cell.a['title'], 'url': cell.a['href']}
            dirnbr += 1
    while True:
        sel = inputter('Input selected collection number: ', 'cyan')
        try:
            sel = int(sel)
            if sel > 0 and sel < dirnbr:
                if len(foundcollections) > 1 and not args.system:
                    collection = foundcollections[sel-1]['name']
                    collectionurl = foundcollections[sel-1]['url']
                else:
                    collection = collectiontemp[sel]['name']
                    collectionurl = collectiontemp[sel]['url']
                break
            else:
                logger('Input number out of range!', 'red')
        except:
            logger('Invalid number!', 'red')
    
#Get collection directory contents and list contents to available ROMs
resp = requests.get(f'{MYRIENTHTTPADDR}{catalogurl}{collectionurl}', headers=REQHEADERS).text
resp = BeautifulSoup(resp, 'html.parser')
collectiondir = resp.find('table', id='list').tbody.find_all('tr')
for rom in collectiondir[1:]:
    cell = rom.find('a')
    filename = cell['title']
    romname = re.sub(r'\.[(a-zA-Z0-9)]{1,3}\Z', '', filename)
    url = f'{MYRIENTHTTPADDR}{catalogurl}{collectionurl}{cell["href"]}'
    availableroms[romname] = {'name': romname, 'file': filename, 'url': url}

#Compare wanted ROMs and contents of the collection, parsing out only wanted files
for wantedrom in wantedroms:
    if wantedrom in availableroms:
        wantedfiles.append(availableroms[wantedrom])
    else:
        missingroms.append(wantedrom)

#Print out information about wanted/found/missing ROMs
logger(f'Amount of wanted ROMs in DAT-file   : {len(wantedroms)}', 'green')
logger(f'Amount of found ROMs at server      : {len(wantedfiles)}', 'green')
if missingroms:
    logger(f'Amount of missing ROMs at server    : {len(missingroms)}', 'yellow')

#Download wanted files
if not args.list:
    dlcounter = 0
    for wantedfile in wantedfiles:
        dlcounter += 1
        download(args.out, wantedfile, dlcounter, len(wantedfiles))

    logger('Downloading complete!', 'green', False)

#Output missing ROMs, if any
if missingroms:
    logger(f'Following {len(missingroms)} ROMs in DAT not automatically found from server, grab these manually:', 'red')
    for missingrom in missingroms:
        logger(missingrom, 'yellow')
else:
    logger('All ROMs in DAT found from server!', 'green')
