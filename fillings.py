#!/usr/bin/Python
# -*- coding: utf-8 -*

import requests
from lxml import html, etree
from bs4 import BeautifulSoup
from collections import OrderedDict
from datetime import datetime
import os.path

import utils

MAX_ITEMS = 100
BASE_URL = "https://www.sec.gov"

class Company():

    def __init__(self, cik):
        self.cik = cik
        self.url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
        self._get_company_info()
        self.base_url = f"https://www.sec.gov"

    def _get_company_info(self):
        page = requests.get(self.url, verify=False, timeout=20)
        soap = BeautifulSoup(page.content, "html.parser")
        tag = soap.find('span',class_='companyName')
        if tag is None:
            utils.logger.error(f"Failed to locate the 'companyName' tag for cik:{self.cik}, is it an INVALID cik?")
            return

        info = tag.text
        pos = info.find('CIK#')
        if pos is not None:
            self.name = info[0: pos-1]
        else:
            utils.logger.warning("failed to figure out company name for CIK:" + self.cik)
        html_page = html.fromstring(page.content)
        companyInfo = html_page.xpath("//div[@class='companyInfo']")[0] if html_page.xpath("//div[@class='companyInfo']") else None
        if companyInfo is not None:
          indentInfo = companyInfo.getchildren()[1]
          self.sic = indentInfo.getchildren()[1].text if len(indentInfo.getchildren()) > 2 else ""
          self.us_state = indentInfo.getchildren()[3].text if len(indentInfo.getchildren()) > 4 else ""
    
    @staticmethod
    def try_parsing_date(text):
        for fmt in ('%Y/%m/%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d.%m.%y %H:%M:%S'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        raise ValueError('no valid date format found')

    def _get_filings_url(self, filing_type="", prior_to="", ownership="include", no_of_entries=MAX_ITEMS):
        url = self.url + "&type=" + filing_type + "&dateb=" + prior_to + "&owner=" +  ownership + "&count=" + str(no_of_entries)
        return url

    def get_all_filings_page(self, filing_type="", prior_to="", ownership="include", no_of_entries=MAX_ITEMS):
      url = self._get_filings_url(filing_type, prior_to, ownership, no_of_entries)
      page = requests.get(url, verify=False, timeout=20)
      return page
    
    def get_search_results(self, filing_type="", prior_to="", ownership="include", no_of_entries=MAX_ITEMS):
        """
        get the url of 'Filling Detail' pages in time-desending order in a map with url as key and 
        'FILLING_TYPE'/'FILLING_DESC'/'FILLING_DATE'/'FILLING_NO' as dictionary keyed-values
        """
        page = self.get_all_filings_page(filing_type, prior_to, ownership, no_of_entries)
        soap = BeautifulSoup(page.content, "html.parser")
        table = soap.find('table', class_='tableFile2')
        ordered_dict = OrderedDict()
        utils.logger.debug("....Search Results...")
        if table is not None:
            rows = table.find_all('tr')
            for row in rows:
                dic = {}
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                dic["FILLING_TYPE"] = cells[0].text
                # url is the first hyperlink
                url = self.base_url + cells[1].a['href']
                dic["FILLING_DESC"] = cells[2].text
                dic["FILLING_DATE"] = cells[3].text
                dic["FILLING_NO"] = cells[4].text
                utils.logger.debug("\t%s\t%s\t%s", dic["FILLING_DATE"], dic["FILLING_TYPE"], url)
                ordered_dict[url] = dic
        return ordered_dict

    def search_fillings(self, since_date, to_date="", filling_types={"10-K","10-Q","8-K"}):
        """
        get the url of 'Filling Detail' pages for specified document types during a time-frame.
        The result is returned in time-desending order in a map with url as key and 
        'FILLING_TYPE'/'FILLING_DESC'/'FILLING_DATE'/'FILLING_NO' as dictionary keyed-values.
        """
        matched_docs = OrderedDict()
        oldest_date = to_date
        since = self.try_parsing_date(since_date)
        query_more = True
        while query_more:
            docs = self.get_search_results(prior_to=oldest_date)
            utils.logger.debug("...fetched %s items from sever prior to %s", len(docs), oldest_date)
            oldest = datetime.strptime(oldest_date, '%Y/%m/%d')
            for url,dic in docs.items():
                type = dic["FILLING_TYPE"]
                date = self.try_parsing_date(dic["FILLING_DATE"])
                oldest_date = date.strftime('%Y/%m/%d')
                oldest = date
                if date >= since:
                    if any([type in type2 for type2 in filling_types]):
                        matched_docs[url] = dic
                else:
                    break
            
            utils.logger.debug("...oldest item been handled:" + oldest_date)
            query_more = oldest >= since
            utils.logger.debug("...query_more? %s", query_more)
        return matched_docs

    def get_document_urls(self, detail_url, type):
        """
        parse out the url of the document format file from the 'Filling Detail' page
        """
        page = requests.get(detail_url, verify=False, timeout=20)
        soap = BeautifulSoup(page.content, "html.parser")
        table = soap.find('table', summary='Document Format Files')
        urls = []
        if table is not None:
            rows = table.find_all('tr')
            if len(rows) == 0:
                utils.logger.error("Failed to parse table rows in page:%s", detail_url)
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                # url is the first hyperlink
                url = self.base_url + cells[2].a['href']
                doc_type = cells[3].text
                if type == doc_type:
                    urls.append(url)
        else:
            utils.logger.error("Failed to locate the table in page:%s", detail_url)
        return urls

    @staticmethod
    def download_document(url, dir, prefix=""):
        dir = os.path.normpath(dir)
        if len(prefix) is not 0:
            filename = prefix.strip() + "_" + os.path.basename(url)
        filename = os.path.join(dir, filename)
        page = requests.get(url, verify=False, timeout=20)
        with open(filename, "wb") as input:
            input.write(page.content)
        return filename

    def download_documents(self, since_date, to_date, filling_types = {"10-K", "10-Q"}, root_dir="."):
        """
        download documents of the specified types during a period, and return an index file recording details
        about all the files being downloaded in time desending order.
        """
        docs = self.search_fillings(since_date=since_date, to_date=to_date, filling_types=filling_types)
        result_dir = os.path.normpath(os.path.join(root_dir, self.cik))
        os.makedirs(result_dir, exist_ok=True)
        logfilename = os.path.normpath(os.path.join(result_dir, "download.idx")) 
        logfile = open(logfilename, 'w', encoding="UTF-8")
        # download the documents from oldest to latest
        for detail_url,dic in reversed(docs.items()):
            type = dic["FILLING_TYPE"]
            date = dic["FILLING_DATE"]
            date_prefix = str(date)
            for sub in (":", "-", "/", "."):
                date_prefix = date_prefix.replace(sub,"")
    
            for url in self.get_document_urls(detail_url, type):
                filename = self.download_document(url, result_dir, date_prefix)
                line = f'{type}\t{date}\t{filename}\t{detail_url}\n'
                logfile.write(line)
        logfile.close()
        return logfilename
    
