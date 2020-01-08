import utils
from fillings import Company
from analysis import Analysis
if __name__ == '__main__':
    specs = utils.read_specs("./firms.xlsx")
    for spec in specs:
        cik = spec[0]
        target_name = spec[1]
        golden_doc = spec[2]
        acq_name = spec[5]
        try:
            company = Company(cik)
        except Exception as e:
            utils.logger.error(f"Failed to create instance for {acq_name}...\n{utils.traceback.format_exc()}")
            continue
        del company
