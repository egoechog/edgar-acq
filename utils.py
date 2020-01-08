import logging,traceback
import pprint
import xlrd
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def pprint2file(content,filename):
    """
    print2file(page.content, "page.html")
    """
    with open(filename, "w", encoding= "UTF-8") as output:
        # improve the HTML structure in output by using pprint
        pprint.pprint(content, output)

def print2file(content,filename):
    """
    print2file(page.content, "page.html")
    """
    with open(filename, "w", encoding= "UTF-8") as output:
        # improve the HTML structure in output by using pprint
        print(content, file=output)

def read_excel(filename):
    rows = {}
    wb = xlrd.open_workbook(filename, on_demand=True)
    sht = wb.sheet_by_index(0)
    for i in range(sht.nrows):
        rows[i] = sht.row_values(i) 
    wb.release_resources()
    del wb
    return rows

def read_specs(filename, startrow=1, endrow=99999999):
    specs = []
    rows = read_excel(filename)
    for key,value in rows.items():
        # skip the header
        if key <= 0 or key < startrow or key > endrow:
            continue
        date_a = str(value[0])
        date_e = str(value[2])
        cik_no = str(value[2])
        acq_name = str(value[3])
        target_fullname = str(value[4])
        target_name = str(value[6])
        target_name = target_name.replace('&', '&.*')
        try:
            cik=str(int(float(cik_no.strip())))
        except ValueError:
            logger.error(f"Ingore invalid CIK {cik_no} in shreadsheet row:{key} for AcquirorName:{acq_name}")
            continue
        specs.append([cik, target_name, "", date_a, date_e, acq_name, target_fullname])
    return specs
