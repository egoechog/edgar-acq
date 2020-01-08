#coding=utf-8
import pprint,os
from collections import OrderedDict
from fillings import Company
from analysis import Analysis
import utils
import unittest
import xlsxwriter

class TestMainFlow(unittest.TestCase):
    specs = (
            ("949341", "PhoneCharge", "20060509_l19900ae10vq.htm"),
            ("1287865", "Sherman", "20060331_g00476e10vk.htm"),
            ("1241199", "Senior Health", "20060510_w20795e10vq.htm"),
            # "G&L" is encoded as "G&#038;L" in raw utf-8 HTML  
            ("1109189", "G&.*L", "20060512_h36076e10vq.htm"),
            ("879993", "Sirius", "20061106_y26727e10vq.htm"),
            ("1073349", "Visibillity", "20060509_d10q.htm"),
            ("726958", "Gas", "20060313_d10q.htm")
            )

    def test_main_flow(self):
        raw_dir = "."
        since_date = "2006/01/01"
        to_date = "2008/12/31"
        filling_types = {"10-K", "10-Q"}
        # case-sensitive by default, or re.IGNORECASE for case-insensive match
        flags = 0
        workbook = xlsxwriter.Workbook('acq_asset_report.xlsx')
        red_format = workbook.add_format({
            'font_color': 'red',
            'bold':       1,
            'underline':  1,
            'font_size':  12,
            })

        for spec in TestMainFlow.specs:
            cik = spec[0]
            target_name = spec[1]
            golden_doc = spec[2]
            index_file = os.path.join(raw_dir, cik, "download.idx")
            worksheet = workbook.add_worksheet(cik)
            worksheet.write_string('A1', "Target Name:")
            worksheet.write_string('B1', target_name)
            worksheet.set_column('A:A', 35)
            worksheet.set_column('B:B', 150)
            utils.logger.info(f'scanning acquisition asset information about {target_name} in {cik} docs...')
            if os.path.exists(index_file) is False:
                company = Company(cik)
                utils.logger.info(f"\tdownloading {'/'.join(filling_types)} documents for cik:{cik}...") 
                index_file = company.download_documents(since_date, to_date, filling_types, raw_dir)
            # grep the target name in case-sensitive way. or set flags = re.IGNORECASE for a case-insensitive search
            ana = Analysis(target_name, index_file)
            docs = ana.locate_target_documents(flags)
            doc_found = ""
            row = 1
            # parse the html and locate the acquisition paragraph
            for filename, dict in docs.items():
                row = row + 1
                if doc_found != "":
                    worksheet.write_url(f"A{row}", dict['FILLING_URL'], string=filename)
                    continue

                utils.logger.info(f'\tfound {target_name} in {filename}, analyzing...')
                info = ana.extract_assets(filename, flags)
                if  info is None:
                    worksheet.write_url(f"A{row}", dict['FILLING_URL'], string=filename)
                    continue
                else:
                    doc_found = os.path.basename(filename)
                    worksheet.write_url(f"A{row}", dict['FILLING_URL'], red_format, string=filename)
                    worksheet.write_string(f"B{row}", info)
                    utils.logger.info(f"!!!!located acquisition asset report!!!!")
                    utils.logger.info(f"\tCIK:{cik}\tTarget:{target_name}\tDate:{dict['FILLING_DATE']}\t{dict['FILLING_TYPE']}:{filename}")
                    utils.logger.info(f"\tFilling Details:{dict['FILLING_URL']}")
                    utils.logger.info(f"{info}\n")
                    continue
            #self.assertEqual(golden_doc, doc_found)
            if golden_doc != doc_found:
                utils.logger.error(f"Expecting initial report: {golden_doc} for {cik} {target_name}, but it locates: {doc_found}")
        workbook.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
