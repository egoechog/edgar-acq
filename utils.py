import logging
import pprint
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

