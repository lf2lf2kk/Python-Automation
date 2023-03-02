import glob
import commentjson
import os
import sys


def validating(input_dir, root_dir, config_dir, input_videos, config_file):
    current = 1
    for input_video in input_videos:
        the_video = input_video.split('\\')[-1]

        with open(config_file, 'r') as f:
            temp_config = commentjson.load(f)

        temp_config["settings"]["timezone"] = "US/Central"
        os.environ["timezone"] = "US/Central"

        temp_config['input']['url'] = '{}\\{}'.format(input_dir, the_video)
        temp_config["output"]["video"] = '{}\\Valid-{}\\output'.format(root_dir, current)
        temp_config["output"]["log"] = '{}\\Valid-{}\\log'.format(root_dir, current)
        new_config_filename = '{}\\{}.jsonc'.format(config_dir, current)

        with open(new_config_filename, 'w') as f1:
            commentjson.dump(temp_config, f1, indent=4)

        os.environ["ConfigPath"] = new_config_filename

        os.system('python3'
                  ' camera_server.py')
        current += 1
    

camera_list = [
    {
        "cam": 'Sam1',
        "config": "configs/cam-1.jsonc"
    },
    {
        "cam": 'Sam2',
        "config": "configs/cam-1.jsonc"
    }
]

cur = 1
for cam in camera_list:
    in_dir = 'C:\\Users\\lf2lf\\Desktop\\' + cam["cam"] + '\\Original'
    rt_dir = 'C:\\Users\\lf2lf\\Desktop\\' + cam["cam"] + '\\Validation'
    config_valid_dir = 'C:\\Users\\lf2lf\\Desktop\\' + cam["cam"] + '\\Validation\\Config'
    videos = os.listdir(in_dir)
    validating(in_dir, rt_dir, config_valid_dir, videos, cam["config"])
    cur += 1

sys.exit(0)
