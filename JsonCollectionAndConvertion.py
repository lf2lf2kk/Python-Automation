import sys
import time
import json
import shutil
import pandas as pd
from os import listdir, rename, path

BAR_FILLER = 1
NUM_OF_VIDEOS = 0
PATH_OF_VALIDATION_JSONS = "C:\\Users\\Desktop\\Client\\Validation\\"
DESTINATION_FOLDER_FOR_JSON = "C:\\Users\\Desktop\\Client\\Validation\\Jsons"
EXCEL_FILENAME_WITH_PATH = './Validation.xlsx'

""" 
Command Line Instruction 
@params:
        -p      <Abosolute Path for Validation Jsons Folder>    - Optional ep: "C:\\Users\\Desktop\\Client\\Validation\\"
        -bar    <Number for Bar Option>                         - Optional (Default: 1)
        -dir    <Destination for Jsons Files>                   - Optional ep: "C:\\Users\\Desktop\\Client\\Validation\\Jsons"
        -n      <Number of Videos>                              - Optional  
        -e      <Excel Name with Path>                          - Optional ep: './Validation.xlsx'
"""


def PrintArgumentHelp():
    print("\nCommand Line Instruction\n\n")
    print("-p      <Abosolute Path for Validation Jsons Folder>    - Optional ep: \"C:\\Users\\Desktop\\Client\\Validation\\\"\n\n")
    print("-bar    <Number for Bar Option>                         - Optional (Default: 1)\n\n")
    print("-dir    <Destination for Jsons Files>                   - Optional ep: \"C:\\Users\\Desktop\\Client\\Validation\\Jsons\"\n\n")
    print("-n      <Number of Videos>                              - Optional \n\n")
    print("-e      <Excel Name with Path>                          - Optional ep: \'./Validation.xlsx\'\n\n")


all_arguments = sys.argv
all_arguments.pop(0)
length_of_arguments = len(all_arguments)
if (length_of_arguments % 2 == 1):
    PrintArgumentHelp()
    exit(0)


for num in range(0, length_of_arguments, 2):
    action = " ".join([all_arguments[num], all_arguments[num + 1]])
    if ('-p' in action.split(' ')):
        PATH_OF_VALIDATION_JSONS = all_arguments[num + 1]
    if ('-bar' in action.split(' ')):
        BAR_FILLER = int(all_arguments[num + 1])
    if ('-dir' in action.split(' ')):
        DESTINATION_FOLDER_FOR_JSON = all_arguments[num + 1]
    if ('-n' in action.split(' ')):
        NUM_OF_VIDEOS = int(all_arguments[num + 1])
    if ('-e' in action.split(' ')):
        EXCEL_FILENAME_WITH_PATH = all_arguments[num + 1]


def PrintProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill=BAR_FILLER, printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """

    FILLER_OPTION = {
        1: '█',
        2: '*',
        3: '#',
        4: 'O',
        5: '+',
        6: 'V',
        7: '?',
        8: '$',
        9: '@',
        10: '[',
        11: '衝',
        12: '難',
        13: '火',
        14: '跑'
    }

    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)

    bar = FILLER_OPTION[fill] * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def JsonMaking():
    current_state = 0
    # Initial the progress bar in terminal
    PrintProgressBar(
        0, NUM_OF_VIDEOS, prefix='Generating Json Files:', suffix=(str(current_state)), length=50)
    for num in range(1, NUM_OF_VIDEOS + 1):
        path_name = PATH_OF_VALIDATION_JSONS + "Valid-" + str(num)
        files = listdir(path_name)

        for filename in files:
            if (filename.endswith(".json")):
                # Make copy file to new folder
                src_file = path.join(path_name + "\\" + filename)
                shutil.copy2(src_file, DESTINATION_FOLDER_FOR_JSON)
                # Rename the file in new folder for later processing purpose
                rename(path.join(DESTINATION_FOLDER_FOR_JSON + "\\" + filename),
                       path.join(DESTINATION_FOLDER_FOR_JSON + "\\" + str(num) + ".json"))

        # Print out the progress in terminal
        time.sleep(0.1)
        PrintProgressBar(current_state + 1, NUM_OF_VIDEOS,
                         prefix='Generating Json Files:', suffix=(str(num) + "/" + str(NUM_OF_VIDEOS)), length=50)
        current_state += 1


def JsonFileConvert():
    complete_json_list = []
    # Initial the progress bar in terminal
    current_state = 0
    PrintProgressBar(
        0, NUM_OF_VIDEOS, prefix='Convert Json to Excel:', suffix=(str(current_state)), length=50)
    for i in range(1, NUM_OF_VIDEOS + 1):
        path = DESTINATION_FOLDER_FOR_JSON + "\\" + str(i) + ".json"

        json_file = open(path)
        json_data = json.load(json_file)
        # Read each instance from the json file and collect them
        for detail in json_data['instance_details']:
            complete_json_list.append(
                {"Video": str(i), "personId": detail["personId"], "totalSeconds": detail["totalSeconds"], "soap": detail["soap"]})

        # Print out the progress in terminal
        time.sleep(0.1)
        PrintProgressBar(current_state + 1, NUM_OF_VIDEOS,
                         prefix='Convert Json to Excel:', suffix=(str(i) + "/" + str(NUM_OF_VIDEOS)), length=50)
        current_state += 1
        json_file.close()

    # Export to excel file
    df = pd.DataFrame(complete_json_list)
    df.to_excel(EXCEL_FILENAME_WITH_PATH)


# Start all the processes
JsonMaking()
print("\n")
JsonFileConvert()
