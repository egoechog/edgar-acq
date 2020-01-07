#### What is it?

A python3 program to scrape and download SEC EDGAR documents during a period, and scan and extract the initial acquisition asset report about specified companies.   

#### How to setup the execution environment?

1.  Install latest python3 environment 

2.  Install pip

3.  install all required packages as below:

    ```shell
    pip install -r requirements.txt
    ```

#### How to run the  demo program?

​	The main.py is a demo program that automatically downloads filling documents of specified companies during a period, and it locates the earliest document that mentioned the acquisition of a target company, prints out the matched content, and check against the predefined golden document names to determine whether the info-scan progress works correctly.   

The demo program can be executed by:

```python
python main.py
```

#### How to inspect the scan result?

While the program is running, you should see scan info printed in the console output, and you can redirect the output into a log file for further inspection:

```
python main.py >& output.log
```

An excel file acq_asset_report.xlsx will be created in current workspace, which collects all the documents matching the target name, and the document mentioned the earliest acquisition is highlighted in red in column-A, and the first acquisition paragraph is filled in column-B.  

BTW, for easing the console output, the HTML table if extracted,  is converted into CVS format which uses comma as delimiter.  The MS Excel program support CVS file format, so you can review the table in MS Excel as following:

1. copy the CVS content and save it into a *.csv file with utf-8 encoding 
2. start up MS Excel, and select to open the saved *.csv file
3. Select the following options in Excel popup: Text Import Wizard:
    1. Original data type: Delimited
    2. My data has headers:Yes
    3. Delimiters:Comma
    4. Treat consecutive delimiters as one:Yes

#### Code Repository:

The source code is published at GitHub:https://github.com/egoechog/edgar-acq.git

