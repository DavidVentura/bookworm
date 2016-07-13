"""Try and uncompress a source file to a dest dir"""
import zipfile
import os.path
import subprocess

USE_UNRAR = True


def unar(source, dest_dir):
    """Split input into zip or rar and parse accordingly.
    Return source if it's not a zip or rar"""
    if source.lower().endswith("zip"):
        return unzip(source, dest_dir)
    if source.lower().endswith("rar"):
        return unrar(source, dest_dir)

    print("NOT RAR? NOT ZIP? I'm panicking.")
    print("I got %s" % source)
    return [source]


def unzip(source_filename, dest_dir):
    """Unzip source_filename to dest_dir"""
    out = []
    with zipfile.ZipFile(source_filename) as zfile:
        for member in zfile.infolist():
            # Path traversal defense copied from
            # http://hg.python.org/cpython/file/tip/Lib/http/server.py#l789
            words = member.filename.split('/')
            path = dest_dir
            for word in words[:-1]:
                _, word = os.path.splitdrive(word)
                _, word = os.path.split(word)
                if word in (os.curdir, os.pardir, ''):
                    continue
                path = os.path.join(path, word)
            out.append(os.path.join(path, member.filename.split('/')[-1]))
            zfile.extract(member, path)
    return out


def unrar(source, dest_dir):
    """Unzip source to dest_dir. Might use unar or unrar
    based on the flag USE_UNRAR"""
    out = []
    list_files = []
    extract_files = []
    if USE_UNRAR:
        list_files = ["unrar", "lb", source]
        extract_files = ["unrar", "x", "-o+", source, dest_dir]
    else:
        list_files = ["lsar", source]
        extract_files = ["unar", "-f", "-o", dest_dir, source]

    with subprocess.Popen(list_files, stdout=subprocess.PIPE) as proc:
        out = proc.stdout.read().decode('utf-8').split("\n")
        if out[0].endswith(": RAR"):
            del out[0]  # header
        if len(out[-1]) == 0:
            del out[-1]
        # print(out)
    subprocess.run(extract_files, stdout=subprocess.DEVNULL)

    return [os.path.join(dest_dir, file) for file in out]
