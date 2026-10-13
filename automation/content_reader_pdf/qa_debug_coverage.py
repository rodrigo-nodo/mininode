"""Diagnostic counts only: why source glyphs are unassigned in public CSM PDF."""
import io
from urllib.request import Request, urlopen
import pdfplumber

URL = "https://drprod-gphdeze8e5bnfegs.a03.azurefd.net/sites/default/files/2025-06/Politica%20de%20Privacidad%20Sitio%20Web.pdf"

def main():
    with urlopen(Request(URL,headers={"User-Agent":"MininodePDFQA/1.0"}),timeout=30) as response:
        content = response.read(2*1024*1024)
    with pdfplumber.open(io.BytesIO(content),laparams={"boxes_flow":0.5}) as doc:
        for number,page in enumerate(doc.pages,1):
            chars=page.chars
            candidates=page.find_tables(table_settings={"vertical_strategy":"lines","horizontal_strategy":"lines"})
            found=[t for t in candidates if len(t.extract())>=2 and all(len(r)>=2 for r in t.extract())]
            boxes=[tuple(map(float,t.bbox)) for t in found]
            def within(obj, b):
                x=(float(obj["x0"])+float(obj["x1"]))/2
                y=(float(obj["top"])+float(obj["bottom"]))/2
                return b[0]<=x<=b[2] and b[1]<=y<=b[3]
            kept=page.filter(lambda obj: obj.get("object_type")!="char" or not any(within(obj,b) for b in boxes))
            ownership={id(ch):i for i,ch in enumerate(chars)}
            counts={}
            for line in kept.extract_text_lines(layout=False,strip=True,return_chars=True):
                for c in line["chars"]:
                    idx=ownership.get(id(c))
                    if idx is not None: counts[idx]=counts.get(idx,0)+1
            for tab in found:
                for row in tab.rows:
                    for cell in row.cells:
                        if cell:
                            for index,char in enumerate(chars):
                                if within(char,cell):
                                    counts[index]=counts.get(index,0)+1
            expected=[index for index,char in enumerate(chars) if str(char.get("text","")).strip()]
            missing=[i for i in expected if counts.get(i,0)==0]
            duplicated=[i for i in expected if counts.get(i,0)>1]
            print("PAGE",number,"chars",len(chars),"tables",len(found),"missing",len(missing),"duplicated",len(duplicated))
            print("  missing-bbox",[(round(chars[i]["x0"]),round(chars[i]["top"])) for i in missing[:6]])
            print("  duplicate-bbox",[(round(chars[i]["x0"]),round(chars[i]["top"])) for i in duplicated[:6]])
if __name__=="__main__":main()
