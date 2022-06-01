import io
import csv
import zipfile


class CSVFileInMemory:
    def __init__(self, filename: str):
        self.filename = filename + '.csv'
        self.data = io.StringIO()
        self._file = csv.writer(self.data)

    def writerow(self, row: list):
        self._file.writerow(row)

    def writerows(self, rows: list):
        self._file.writerows(rows)

    @property
    def size(self):
        cu = self.data.tell()
        end_pos = self.data.seek(0, io.SEEK_END)
        self.data.seek(cu)
        return end_pos

    def to_bytes(self):
        value = self.data.getvalue()
        return value.encode(encoding='utf-8')

    def close(self):
        self.data.close()

    def to_zip(self):
        zf_buf = io.BytesIO()
        zf = zipfile.ZipFile(zf_buf, 'a', zipfile.ZIP_DEFLATED, False)

        # write the file to the in-memory zip
        self.data.seek(0)
        zf.writestr(zinfo_or_arcname=self.filename, data=self.data.read())
        # mark the files as having been created on Windows
        # so that Unix permissions are not inferred as 0000
        for zfile in zf.filelist:
            zfile.create_system = 0

        return zf_buf
