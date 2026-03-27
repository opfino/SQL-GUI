# How to activate the GUI

I recommend using Anaconda over Python when choosing your PATH

Við Anaconda:
1. Conda (Currently works well with 'base (3.13.5)') must be used as the PATH on your Python or VSC for this to work when using Conda

3. Afterwards, copy and paste this into your Anaconda Prompt. Not Windows cmd:
conda activate base

4. then Download the required pip install:
python -m pip install streamlit pandas oracledb

5. And lastly, copy and paste the folder's full link name. Remember to use the full link in the folder, in addition to adding the file name and "" at the start and end. for example:
python -m streamlit run "C:\Downloads\GUI.py"

6. Then you should get an blue colored word asking for Email. So simply press enter.

7. Then the page should simply just open

8. For as long as Anaconda Prompt is turned on. Do you have an artificial server for the same Wifi. So others sharing your Wifi, can enter this page aswell.


Við Python:
How to run the Banking GUI:

1. Install Python
2. Install required libraries:
   pip install streamlit oracledb pandas

3. Make sure Oracle database is running

4. Update database connection in GUI.py if needed

5. Example for how to run. Remember to use the full link in the folder, in addition to adding the file name and "" at the start and end:
   streamlit run "C:\Downloads\GUI.py"

6. Then you should get an blue colored word asking for Email. So simply press enter.

7. Then the page will load automatically on google.
