import subprocess
import os


def convert_to_1080p(input_path, output_path):
    command = [
        'ffmpeg',
        '-i', input_path,
        '-vf', 'scale=-1:1080',
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Conversion complete! Output saved to {output_path}")
    except subprocess.CalledProcessError as error:
        print(f"An error occurred: {error}")


def main():
    input_folder = "C:\\Users\\lf2lf\\Desktop\\Enhanced-Hygiene\\Non-Hygiene"
    output_folder = "C:\\Users\\lf2lf\\Desktop\\1080Converted\\Non-Hygiene-Converted"

    if not os.path.exists(input_folder):
        print(f"Input folder not found: {input_folder}")
        return

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.flv')

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(video_extensions):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(
                output_folder, f"{os.path.splitext(filename)[0]}-1080p{os.path.splitext(filename)[1]}")
            print(f"Converting {filename} to 1080p...")
            convert_to_1080p(input_path, output_path)


if __name__ == '__main__':
    main()
