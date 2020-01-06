#!/usr/bin/Python
# -*- coding: utf-8 -*

from bs4 import BeautifulSoup
from bs4 import NavigableString
from nltk import word_tokenize
from collections import OrderedDict
import mmap,re,io,csv,os
import utils

class Analysis():
    # "FINANCIAL STATEMENTS" for case:Gas,726958, but it causes Case G&L,1109189 reporting
    # older doc , the case Visibillity,1073349 fails due to the same reason. 
    acq_title_words = {"Acquisition", "Goodwill", "Intangible Assets", "Purchase Price", "Initial Costs",
            "FINANCIAL STATEMENTS"}
    acq_text_words = {"acquisition", "acquired", "purchase price",
        "purchased", "initial purchase", "was allocated"}
    asset_words = {"Intangible", "goodwill", "fair value of the asset", "Initial Cost"}
    acq_exclude_words = {"acquisition will operate", "no later than", "in the future"}
    asset_table_following_indicators = {"acquisition", "acquired"}

    def __init__(self, targetname, indexfile):
        self.target_name = targetname
        self.index_file = indexfile
        escaped_words = [re.escape(word) for word in Analysis.acq_title_words]
        self.acq_title_pattern = "|".join(escaped_words)
        escaped_words = [re.escape(word) for word in Analysis.acq_text_words]
        self.acq_pattern = "|".join(escaped_words)
        escaped_words = [re.escape(word) for word in Analysis.asset_words]
        self.asset_pattern = "|".join(escaped_words)
        escaped_words = [re.escape(word) for word in Analysis.asset_table_following_indicators]
        self.asset_table_indicators_pattern = "|".join(escaped_words)
        escaped_words = [re.escape(word) for word in Analysis.acq_exclude_words]
        self.acq_exclude_pattern = "|".join(escaped_words)

    @staticmethod
    def full_text_search(filename, pattern, flags = 0):
        """
        Scan through a string 'pattern' in the specified file, return the 
        matched sequence or None.
        """
        with open(filename, 'rb', 0) as file:
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                match = re.search(bytes(pattern, encoding='utf8'), mm, flags)
                if match:
                    return match.group()
        return None

    def locate_target_documents(self, flags = 0):
        """
        figure out the documents containing the specified target name pattern in time-asending order.
        """
        lines = []
        with open(self.index_file, 'r', encoding="UTF-8") as input:
            lines = input.readlines()
        docs = OrderedDict()
        for line in lines:
            items = line.split("\t")
            dict = {}
            dict["FILLING_TYPE"] = items[0]
            dict["FILLING_DATE"] = items[1]
            filename = items[2]
            dict["FILLING_URL"] = items[3]
            if Analysis.full_text_search(filename, self.target_name, flags) is not None:
                docs[filename] = dict
                utils.logger.debug(f'{dict["FILLING_DATE"]}:match {self.target_name} in {dict["FILLING_TYPE"]} doc:{filename}')
        return docs

    def guess_acquisition_title(self, tag, flags=0):
        # ignore long text
        raw_txt = tag.get_text()
        if len(raw_txt) > 150:
            return False 
        # ignore the hyperlinks which probably are table of contents
        a_tag = tag.parent.find('a', href=True)
        if a_tag is not None:
            return False
        # ignore NavigableString
        if isinstance(tag, NavigableString):
            return False
        if re.search(self.acq_title_pattern, raw_txt, flags) is None:
            return False
        utils.logger.debug(f"new possible title found:{raw_txt}")
        return True

    def locate_acquisition_info(self, tag, flags=0):
        info = None
        # suppose the acquisition statement text exists within the following parent tags: 
        whitelist = ['p', 'div', 'tr']
        if tag.name not in whitelist:
            utils.logger.debug(f"{tag.name} not in white tag list")
            return info
        # suppose the desired text exists in either <font> or <div> tag
        text_elements = [t for t in tag.find_all(['font', 'div'])]
        if len(text_elements) == 0 and tag.name == 'div':
            utils.logger.debug(f"no child div elements found")
            text_elements = [tag]
        # determine whether it is the text desired
        for txt_elt in text_elements:
            # ignore the hyperlinks which probably are table of contents
            a_tag = txt_elt.parent.find('a', href=True)
            if a_tag is not None:
                utils.logger.debug(f"ignore hyperlink")
                continue
            raw_txt = txt_elt.get_text()
            # ignore NavigableString
            if isinstance(txt_elt, NavigableString):
                continue
            # match the target name
            if re.search(self.target_name, raw_txt, flags) is None:
                continue
            # then match any acquisition keywords without the any excluding words
            if re.search(self.acq_pattern, raw_txt, flags) is None:
                continue
            if re.search(self.acq_exclude_pattern, raw_txt, flags) is not None:
                continue
            info = self.composite_info(info, raw_txt)
            # TBD... it is OK to suppose acquisition information doesn't across paragraghs??
            break
        return info
    
    def find_ancestor(self, tag, ancestornames:list):
        parent = tag.parent
        while parent != None and parent.name not in ancestornames:
            parent = parent.parent
        return parent
    
    def composite_info(self, oldinfo, newinfo, title=None):
        info = oldinfo
        if info is None:
            info = newinfo + "\n"
        else:
            info = info + newinfo + "\n"
        if title is not None and title != "":
            info = title + "\n" + info
        return info

    @staticmethod
    def get_table_headers(table):
        """Given a table soup, returns all the headers"""
        headers = []
        for th in table.find("tr").find_all("th"):
            headers.append(th.text.strip())
        return headers
    
    @staticmethod
    def get_logical_headers(table):
        # if the headers are well defined with <th>, just get them and return
        headers = Analysis.get_table_headers(table)
        if len(headers) > 0:
            return headers
        # need to figure out the table headers from the rows data
        # suppose the header is bold and center-alligned
        dict = {}
        for tr in table.find_all("tr")[1:]:
            # grab all td tags in this table row
            tds = tr.find_all("td")
            if len(tds) == 0:
                # if no td tags, search for th tags
                ths = tr.find_all("th")
                idx = 0
                for th in ths:
                    txt = th.text.strip()
                    if th.has_attr("align") and None != th.find("b"):
                        dict[idx] = f"{dict[idx]} {txt}" if idx in dict else txt
                    elif idx in dict:
                        break
                    idx += 1
            else:
                # use regular td tags
                idx = 0
                for td in tds:
                    txt = td.text.strip()
                    if td.has_attr("align") and td['align'] == "center" and None != td.find("b"):
                        dict[idx] = f"{dict[idx]} {txt}" if idx in dict else txt
                    elif idx in dict:
                        break
                    idx += 1
        headers = [str(item) for item in dict.values()]
        return headers

    @staticmethod
    def get_table_rows(table):
        """Given a table, returns all its rows"""
        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = []
            # grab all td tags in this table row
            tds = tr.find_all("td")
            if len(tds) == 0:
                # if no td tags, search for th tags
                ths = tr.find_all("th")
                for th in ths:
                    txt = th.text.strip()
                    if txt == "$":
                        continue
                    cells.append(txt)
            else:
                # use regular td tags
                for td in tds:
                    txt = td.text.strip()
                    if txt == "$":
                        continue
                    cells.append(txt)
            rows.append(cells)
        return rows

    @staticmethod
    def table2csv(table, csvoutput):
        """
        common delimited, treat consecutive delimiters as one, text qualified by "
        """
        writer = csv.writer(csvoutput)
        headers = Analysis.get_table_headers(table)
        writer.writerow(headers)
        
        rows = Analysis.get_table_rows(table)
        for row in rows:
            writer.writerow(row)

    def extract_table_section(self, table):
        """
        determine whether both the title and acquisition info is enclosed within the 
        same table, if true then extract the table as csv data, otherwise return None  
        """
        table_raw = table.get_text()
        # if the targetname and any asset keywords exist in the table, it is the right one 
        if re.search(self.target_name, table_raw) is not None:
            if re.search(self.asset_pattern, table_raw, re.IGNORECASE) is not None:
                csv_output = io.StringIO()
                self.table2csv(table, csv_output)
                return self.composite_info(None, csv_output.getvalue())
        return None

    def extract_assets(self, filename, flags = 0):
        """
        try to extract acquisition asset information about the target company.
        1. sometimes the text is in <font> like the last 2 ciks; but it could also be
            in <div> like the first two ciks; Note that performance gets much worser after
            parsing the <div> tags. 
            And the acquisition could be mentioned in Summary or Subsequent Event sections
            earlier without detailed asset report, so there must be a way to skip such fake
            information. Probably we can try to locate and focus on the Acquisition section. 
        2. most page has the bold/italic title and we should be able to locate the 
            Acquisition section by the title, then parse the text and asset table;
            but some page could put all texts in a table and we may need to extract the
            table instead.
        """
        html = None
        info = None
        if os.path.exists(filename) is False:
            return info

        with open(filename, 'rb') as input:
            html = input.read()
        soup = BeautifulSoup(html, 'html.parser', from_encoding="UTF-8")
        # locate the ../<description>/<text>
        desc_tag = soup.find('description')
        if desc_tag is None:
            return info
        text_tag = desc_tag.find('text')
        if text_tag is None:
            return info

        section_found = False
        title_elements =text_tag.find_all('b')
        for title in title_elements:
            # 1>. figure out a possible section title
            # search in case-insensitive way, the title could all in uppercases
            # like the case Sirius,879993 'BUSINESS ACQUISITION'
            if self.guess_acquisition_title(title, re.IGNORECASE) is False:
                continue
            utils.logger.info(f'\tpossible acquisition title?\n{title.get_text()}')
            # then check whether the ancestor <div>/<p>/<tr> exists 
            ancestor = self.find_ancestor(title, ['p', 'div', 'tr'])
            if ancestor is None:
                continue
            next = ancestor.findNextSibling(['p', 'div', 'tr'])
            # 2>. handle several cases that the title exists in a table
            if ancestor.name == "tr":
                table = self.find_ancestor(ancestor, ['table'])
                if None == next:
                    # no any subsequent rows exist, try to parse the <div> 
                    # sibling next to the table instance which is the case
                    # Senior Health,1241199
                    next = table.findNextSibling('div')
                elif next.name == 'tr':
                    # subsequent rows exist, this is the case Sherman,1287865 where
                    # both title and acquisition info exist in the same table
                    table_info = self.extract_table_section(table)
                    if None != table_info:
                        section_found = True
                        return self.composite_info(info, table_info)
            
            # 3>. iterate the siblings to determine whether it is a desired section; if yes
            # then extract the acquisition infomation 
            new_title_found = False  
            while next is not None:
                # break out if a new possible section title is found
                for new_title in next.find_all('b'):
                    if self.guess_acquisition_title(new_title, re.IGNORECASE):
                        new_title_found = True
                        break
                if new_title_found:
                    break
                
                # try to extract the acquisition info which should exist in the next sibling
                # tags like <div>,<p> or <tr>
                utils.logger.debug(f'\tlocating acqusition info within <{next.name}>')
                acq_txt = self.locate_acquisition_info(next, flags)
                if acq_txt is not None:
                    utils.logger.debug(f"\tsuccessfully located acqusition info:\n{acq_txt}")
                    section_found = True
                    info = self.composite_info(info, acq_txt)
                    # TBD... extract the asset table if exist
                    # TBD... determine how to break out from extracting loop 
                
                next = next.findNextSibling(['p', 'div', 'tr'])
                
                # 4>. break out from the document if the desired section is located 
                if section_found:
                    break
        return info
