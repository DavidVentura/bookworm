import zipfile,os.path
import subprocess

USE_UNRAR=True

def unar(source,dest_dir):
    if source.lower().endswith("zip"):
        return unzip(source,dest_dir)
    if source.lower().endswith("rar"):
        return unrar(source,dest_dir)

    print("NOT RAR? NOT ZIP? I'm panicking.")
    print("I got %s" % source)
    return [source]

def unzip(source_filename, dest_dir):
    out=[]
    with zipfile.ZipFile(source_filename) as zf:
        for member in zf.infolist():
            # Path traversal defense copied from
            # http://hg.python.org/cpython/file/tip/Lib/http/server.py#l789
            words = member.filename.split('/')
            path = dest_dir
            for word in words[:-1]:
                drive, word = os.path.splitdrive(word)
                head, word = os.path.split(word)
                if word in (os.curdir, os.pardir, ''): continue
                path = os.path.join(path, word)
            out.append(os.path.join(path,member.filename.split('/')[-1]))
            zf.extract(member, path)
    return out


def unrar(source, dest_dir):
    out=[]
    list_files=[]
    extract_files=[]
    if USE_UNRAR:
        list_files=["unrar","lb",source]
        extract_files=["unrar","x",source,dest_dir]
    else:
        list_files=["lsar",source]
        extract_files=["unar","-f","-o",dest_dir,source]

    with subprocess.Popen(list_files, stdout=subprocess.PIPE) as proc:
        out=proc.stdout.read().decode('utf-8').split("\n")
        if out[0].endswith(": RAR"):
            del out[0] #header
        if len(out[-1])==0:
            del out[-1]
        #print(out)
    subprocess.run(extract_files,stdout=subprocess.DEVNULL)

    return [os.path.join(dest_dir,file) for file in out ]
