import os
import sys

def listdir_nohidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            yield f

def str_size(nbyte):
    k = 0
    while nbyte >> (k + 10):
        k += 10
    units = ("B", "KB", "MB", "GB")
    size_by_unit = round(nbyte / (1 << k), 2) if k else nbyte
    return str(size_by_unit) + units[k // 10]

class Tree():
    mode_descriptions = {
        'df': 'Directory First',
        'do': 'Directory Only',
        'ff': 'File First',
        'od': 'Ordered'
    }

    def __init__(self, path, indent=4, mode='ff', sparse=True, dtail='/',
        show_hidden=False, show_size=False):
        self.sparse = sparse
        self.dtail = dtail
        self.indent_space = ' ' * indent
        self.down_space = '│' + ' ' * (indent - 1)
        self.vert_horiz = '├' + '─' * (indent - 1)
        self.turn_horiz = '└' + '─' * (indent - 1)

        self.traverses = {
            'df': self.df,
            'do': self.do,
            'ff': self.ff,
            'od': self.od
        }
        self.listdir = os.listdir if show_hidden else listdir_nohidden
        self.show_size = show_size

        self.chmod(mode)
        self.generate(path)

    def write(self, filename):
        with open(filename, 'w+', encoding='utf-8') as fd:
            fd.write('mode: %s\n' % self.mode)
            fd.write('\n')
            fd.write(self.tree)

    def print(self):
        print(self.tree)

    def chmod(self, mode):
        assert mode in self.traverses
        self.traverse = self.traverses[mode]
        self.mode = self.mode_descriptions[mode]

    def generate(self, path):
        """
        metadata: [(path, isfile?, size) or None], maybe use to open file
        size: file size, or number of files in a Directory, is a string
        """
        path = os.path.abspath(path)
        assert os.path.isdir(path)
        self.metadata = []
        self.lines = [path]
        self.traverse(path, '')

        if self.lines[-1] == '':
            self.lines.pop()
            self.metadata.pop()

        if self.show_size:
            sep = self.indent_space or ' '
            size_len = max(len(md[2]) for md in self.metadata if md)
            for i, mdata in enumerate(self.metadata):
                size = mdata[2] if mdata else ' '
                size = '%*s' % (size_len, size)
                self.lines[i] = size + sep + self.lines[i]

        self.tree = '\n'.join(self.lines) + '\n'

    def get_dirs_files(self, dirpath):
        dirs, files = [], []
        for leaf in self.listdir(dirpath):
            path = os.path.join(dirpath, leaf)
            if os.path.isfile(path):
                files.append((leaf, path))
            else:
                dirs.append((leaf, path))
        self.metadata.append((dirpath, False, str(len(dirs) + len(files))))

        return dirs, files

    def add_dirs(self, dirs, prefix, fprefix, dprefix, recursive):
        for dirname, path in dirs[:-1]:
            self.lines.append(dprefix + dirname + self.dtail)
            recursive(path, fprefix)

        dirname, path = dirs[-1]
        fprefix = prefix + self.indent_space
        dprefix = prefix + self.turn_horiz
        self.lines.append(dprefix + dirname + self.dtail)
        recursive(path, fprefix)

    def add_files(self, files, fprefix):
        for filename, path in files:
            size = str_size(os.path.getsize(path))
            self.lines.append(fprefix + filename)
            self.metadata.append((path, True, size))
        if self.sparse and files:
            self.lines.append(fprefix.rstrip())
            self.metadata.append(None)

    def df(self, dirpath, prefix):
        dirs, files = self.get_dirs_files(dirpath)
        if dirs:
            fprefix = prefix + self.down_space
            dprefix = prefix + self.vert_horiz
            self.add_dirs(dirs, prefix, fprefix, dprefix, self.df)
            self.add_files(files, prefix + self.indent_space)

        else:
            self.add_files(files, prefix + self.indent_space)

    def do(self, dirpath, prefix):
        dirs = []
        for leaf in self.listdir(dirpath):
            path = os.path.join(dirpath, leaf)
            if os.path.isdir(path):
                dirs.append((leaf, path))
        self.metadata.append((dirpath, False, str(len(dirs))))
        if dirs:
            fprefix = prefix + self.down_space
            dprefix = prefix + self.vert_horiz
            self.add_dirs(dirs, prefix, fprefix, dprefix, self.do)

    def ff(self, dirpath, prefix):
        dirs, files = self.get_dirs_files(dirpath)
        if dirs:
            fprefix = prefix + self.down_space
            dprefix = prefix + self.vert_horiz
            self.add_files(files, fprefix)
            self.add_dirs(dirs, prefix, fprefix, dprefix, self.ff)
        else:
            self.add_files(files, prefix + self.indent_space)

    def od(self, dirpath, prefix):
        def add_leaf(leaf):
            path = os.path.join(dirpath, leaf)
            if os.path.isfile(path):
                size = str_size(os.path.getsize(path))
                self.lines.append(dprefix + leaf)
                self.metadata.append((path, True, size))
            if os.path.isdir(path):
                self.lines.append(dprefix + leaf + self.dtail)
                self.od(path, fprefix)

        leaves = sorted(self.listdir(dirpath))
        self.metadata.append((dirpath, False, str(len(leaves))))

        if not leaves:
            return

        fprefix = prefix + self.down_space
        dprefix = prefix + self.vert_horiz
        for leaf in leaves[:-1]:
            add_leaf(leaf)

        fprefix = prefix + self.indent_space
        dprefix = prefix + self.turn_horiz
        add_leaf(leaves[-1])
