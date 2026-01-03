import os
import sys
import subprocess
import argparse
import shutil

# Copyright (C) 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

def check_dependencies():
    """Checks if ffmpeg and ffprobe are available and executable."""
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')

    if not ffmpeg_path or not ffprobe_path:
        print("Error: ffmpeg or ffprobe not found in system PATH.")
        print_install_help()
        sys.exit(1)
        
    # verify they actually run (catches missing DLLs issues on Windows)
    try:
        subprocess.run([ffmpeg_path, '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run([ffprobe_path, '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.CalledProcessError, OSError):
        print(f"Error: ffmpeg or ffprobe was found but failed to run.")
        print("This often happens if you downloaded a 'shared' build but are missing the DLLs.")
        print("Please download a 'static' or 'full' build.")
        print_install_help()
        sys.exit(1)

    return ffmpeg_path, ffprobe_path

def print_install_help():
    print("Please install ffmpeg (static build) and ensure executable is in PATH.")
    print("  - Windows: https://www.gyan.dev/ffmpeg/builds/ (ffmpeg-git-full.7z)")
    print("  - Linux: sudo apt install ffmpeg")
    print("  - macOS: brew install ffmpeg")

import json

def get_file_info(file_path):
    """
    Gets audio file information using ffprobe.
    Returns a dictionary containing duration (sec), sample_rate, and channels.
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'a:0',
        '-show_entries', 'stream=sample_rate,channels',
        '-show_entries', 'format=duration',
        '-of', 'json',
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Format info
        duration = float(data['format']['duration'])
        
        # Stream info
        if not data.get('streams'):
            raise ValueError("No audio stream found")
            
        stream = data['streams'][0]
        sample_rate = int(stream['sample_rate'])
        channels = int(stream['channels'])
        
        return {
            'duration': duration,
            'sample_rate': sample_rate,
            'channels': channels
        }
    except subprocess.CalledProcessError as e:
        print(f"Error getting info for {file_path}: {e}")
        sys.exit(1)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing info for {file_path}: {e}")
        sys.exit(1)

def escape_metadata(text):
    """Escapes special characters for FFMETADATA file."""
    # =, ;, #, \ and newline must be escaped with a backslash
    text = text.replace('\\', '\\\\')
    text = text.replace('=', '\\=')
    text = text.replace(';', '\\;')
    text = text.replace('#', '\\#')
    return text

def print_verbose(msg, verbose):
    if verbose:
        print(f"[VERBOSE] {msg}")

class ProgressBar:
    def __init__(self, total, prefix='', suffix='', decimals=1, length=50, fill='█', printEnd="\r"):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.printEnd = printEnd
        self.iteration = 0

    def print_progress(self, iteration):
        self.iteration = iteration
        percent = ("{0:." + str(self.decimals) + "f}").format(100 * (self.iteration / float(self.total)))
        filledLength = int(self.length * self.iteration // self.total)
        bar = self.fill * filledLength + '-' * (self.length - filledLength)
        print(f'\r{self.prefix} |{bar}| {percent}% {self.suffix}', end=self.printEnd)
        # Print New Line on Complete
        if self.iteration == self.total:
            print()

def main():
    parser = argparse.ArgumentParser(description="Join MP3 files into a chapterized M4B (MP4) file without re-encoding.")
    parser.add_argument("input_dir", help="Directory containing the MP3 files")
    parser.add_argument("order_file", help="Text file specifying the order of files (filename|Chapter Title)")
    parser.add_argument("output_file", help="Output .m4b filename")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--cover", help="Path to cover image (jpg/png) to embed")
    
    args = parser.parse_args()

    check_dependencies()

    input_dir = args.input_dir
    order_file_path = args.order_file
    output_file = args.output_file
    cover_image_path = args.cover

    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)
    
    if not os.path.isfile(order_file_path):
        print(f"Error: Order file '{order_file_path}' does not exist.")
        sys.exit(1)
        
    if cover_image_path and not os.path.isfile(cover_image_path):
        print(f"Error: Cover image '{cover_image_path}' not found.")
        sys.exit(1)

    chapters = []
    file_list = []

    print("Reading order file and analyzing audio files...")
    
    try:
        with open(order_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading order file: {e}")
        sys.exit(1)

    current_time_ns = 0

    # Temporary files
    concat_list_path = os.path.join(input_dir, 'files_to_concat.txt')
    metadata_path = os.path.join(input_dir, 'metadata.txt')

    analysis_ref = None # To store parameters of the first file for comparison
    
    # Filter lines for real content often to get accurate total count for progress bar
    valid_lines = [line.strip() for line in lines if line.strip()]
    total_files = len(valid_lines)
    
    progress_bar = ProgressBar(total_files, prefix='Processing:', suffix='Complete', length=40)
    
    print(f"Found {total_files} files to process.")

    try:
        with open(concat_list_path, 'w', encoding='utf-8') as concat_file:
            for i, line in enumerate(valid_lines):
                parts = line.split('|')
                filename = parts[0].strip()
                if len(parts) > 1:
                    chapter_title = parts[1].strip()
                else:
                    chapter_title = os.path.splitext(filename)[0]

                file_path = os.path.join(input_dir, filename)
                
                if not os.path.isfile(file_path):
                    print(f"\nWarning: File '{filename}' not found in input directory. Skipping.")
                    continue

                print_verbose(f"Analyzing: {filename}", args.verbose)
                info = get_file_info(file_path)
                print_verbose(f"  Duration: {info['duration']}s, Rate: {info['sample_rate']}Hz", args.verbose)
                
                # Validation Logic
                if analysis_ref is None:
                    analysis_ref = info
                    print_verbose(f"Reference parameters set: {analysis_ref['sample_rate']}Hz, {analysis_ref['channels']} channels", args.verbose)
                else:
                    if info['sample_rate'] != analysis_ref['sample_rate']:
                        print(f"\nError: Sample rate mismatch in '{filename}'.")
                        print(f"Expected {analysis_ref['sample_rate']}Hz, found {info['sample_rate']}Hz.")
                        print("All input files must have the same sample rate.")
                        sys.exit(1)
                    if info['channels'] != analysis_ref['channels']:
                        print(f"\nError: Channel count mismatch in '{filename}'.")
                        print(f"Expected {analysis_ref['channels']} channels, found {info['channels']} channels.")
                        print("All input files must have the same channel count.")
                        sys.exit(1)

                duration_ns = int(info['duration'] * 1_000_000_000)

                start_time = current_time_ns
                end_time = current_time_ns + duration_ns
                current_time_ns = end_time

                chapters.append({
                    'title': chapter_title,
                    'start': start_time,
                    'end': end_time
                })
                
                # IMPORTANT: ffmpeg concat demuxer requires safe filenames. 
                # We simply quote the path.
                safe_path = file_path.replace('\\', '/')
                concat_file.write(f"file '{safe_path}'\n")
                
                progress_bar.print_progress(i + 1)
    
    except Exception as e:
        print(f"\nError processing files: {e}")
        sys.exit(1)

    if not chapters:
        print("No valid files found to process.")
        sys.exit(1)

    print("Generating metadata file...")
    with open(metadata_path, 'w', encoding='utf-8') as meta_file:
        meta_file.write(";FFMETADATA1\n")
        for chapter in chapters:
            meta_file.write("[CHAPTER]\n")
            meta_file.write("TIMEBASE=1/1000000000\n") # Nanosecond timebase
            meta_file.write(f"START={chapter['start']}\n")
            meta_file.write(f"END={chapter['end']}\n")
            meta_file.write(f"title={escape_metadata(chapter['title'])}\n")

    print("Joining files...")
    # ffmpeg command
    # -f concat: use concat demuxer
    # -safe 0: allow unsafe file paths (absolute paths)
    # -i concat_list_path: input file list
    # -i metadata_path: input metadata
    # -map_metadata 1: use metadata from the second input (metadata.txt)
    # -c copy: copy streams (no re-encode)
    # -map 0:a: use audio from first input
    # -y: overwrite output
    
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_list_path,
        '-i', metadata_path
    ]

    # Add cover image input if provided
    if cover_image_path:
        print(f"Embedding cover image: {cover_image_path}")
        cmd.extend(['-i', cover_image_path])

    cmd.extend([
        '-map_metadata', '1',
        '-c', 'copy',
        '-map', '0:a'
    ])

    if cover_image_path:
        # Map the cover image stream (input 2)
        # -c:v copy if usage allows, but sometimes safest to let ffmpeg handle it or force mjpeg
        # -disposition:v:0 attached_pic marks it as cover art
        cmd.extend([
            '-map', '2:v',
            '-c:v', 'copy',
            '-disposition:v:0', 'attached_pic',
            '-metadata:s:v', 'title="Album cover"',
            '-metadata:s:v', 'comment="Cover (front)"' 
        ])

    cmd.extend([
        '-f', 'mp4',
        '-y',
        output_file
    ])

    try:
        subprocess.run(cmd, check=True)
        print(f"Success! Output saved to: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error running ffmpeg: {e}")
    finally:
        # Cleanup temporary files
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

if __name__ == "__main__":
    main()
