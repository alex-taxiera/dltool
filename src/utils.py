import os
import math
import datetime
import platform
import requests
from progressbar import ProgressBar, Bar, ETA, FileTransferSpeed, Percentage, DataSize
from retry import retry

from src.const import CHUNKSIZE, REQHEADERS
from src.types import RomMeta

#Print output function
def logger(str: str, color=None, rewrite=False):
    colors = {'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m', 'cyan': '\033[96m'}
    if rewrite:
        print('\033[1A', end='\x1b[2K')
    if color:
        print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | {colors[color]}{str}\033[00m')
    else:
        print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | {str}')

#Input request function
def inputter(str: str, color=None):
    colors = {'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m', 'cyan': '\033[96m'}
    if color:
        val = input(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | {colors[color]}{str}\033[00m')
    else:
        val = input(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | {str}')
    return val

#Scale file size
def scale1024(val: int):
    prefixes=['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    if val <= 0:
        power = 0
    else:
        power = min(int(math.log(val, 2) / 10), len(prefixes) - 1)
    scaled = float(val) / (2 ** (10 * power))
    unit = prefixes[power]
    return scaled, unit

#Exit handler function
def exithandler(signum, frame):
    logger('Exiting script!', 'red')
    exit()

@retry(delay=2, backoff=2, tries=5)
def download(outputPath: str, wantedfile: RomMeta, fileIndex: int, totalDownloadCount: int):
    resumedl = False
    proceeddl = True

    if platform.system() == 'Linux':
        localpath = f'{outputPath}/{wantedfile["file"]}'
    elif platform.system() == 'Windows':
        localpath = f'{outputPath}\{wantedfile["file"]}'

    resp = requests.get(wantedfile['url'], headers=REQHEADERS, stream=True)
    remotefilesize = int(resp.headers.get('content-length'))
    
    if os.path.isfile(localpath):
        localfilesize = int(os.path.getsize(localpath))
        if localfilesize != remotefilesize:
            resumedl = True
        else:
            proceeddl = False
    
    if proceeddl:
        file = open(localpath, 'ab')
        
        size, unit = scale1024(remotefilesize)
        pbar = ProgressBar(widgets=['\033[96m', Percentage(), ' | ', DataSize(), f' / {round(size, 1)} {unit}', ' ', Bar(marker='#'), ' ', ETA(), ' | ', FileTransferSpeed(), '\033[00m'], max_value=remotefilesize, redirect_stdout=True, max_error=False)
        pbar.start()
        
        if resumedl:
            logger(f'Resuming    {str(fileIndex).zfill(len(str(totalDownloadCount)))}/{totalDownloadCount}: {wantedfile["name"]}', 'cyan')
            pbar += localfilesize
            headers = REQHEADERS
            headers.update({'Range': f'bytes={localfilesize}-'})
            resp = requests.get(wantedfile['url'], headers=headers, stream=True)
            for data in resp.iter_content(chunk_size=CHUNKSIZE):
                file.write(data)
                pbar += len(data)
        else:
            logger(f'Downloading {str(fileIndex).zfill(len(str(totalDownloadCount)))}/{totalDownloadCount}: {wantedfile["name"]}', 'cyan')
            for data in resp.iter_content(chunk_size=CHUNKSIZE):
                file.write(data)
                pbar += len(data)
        
        file.close()
        pbar.finish()
        print('\033[1A', end='\x1b[2K')
        logger(f'Downloaded  {str(fileIndex).zfill(len(str(totalDownloadCount)))}/{totalDownloadCount}: {wantedfile["name"]}', 'green', True)
    else:
        logger(f'Already DLd {str(fileIndex).zfill(len(str(totalDownloadCount)))}/{totalDownloadCount}: {wantedfile["name"]}', 'green')
