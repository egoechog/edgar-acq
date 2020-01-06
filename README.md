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

#### Code Repository:

The source code is published at GitHub:https://github.com/egoechog/edgar-acq.git

