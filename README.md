# M4B Joiner

A simple Python script to merge multiple MP3 files into a single chapterized M4B (MP4) audiobook file without re-encoding.

## Features

- **No Re-encoding**: Uses `ffmpeg` with `-c copy` to losslessly merge MP3 streams.
- **Validation**: checks that all input MP3s have the same sample rate and channel count to ensure valid output.
- **Chapter Support**: Generates chapters based on input files.
- **Custom Ordering**: Uses a text file to define the order and chapter titles.
- **Cross-Platform**: Works on Windows, Linux, and macOS.

## Prerequisites

1.  **Python 3.x**
2.  **FFmpeg**: Must be installed and added to your system PATH.
    *   **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html), extract it, and add the `bin` folder to your System Environment Variables -> PATH.
    *   **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo pacman -S ffmpeg` (Arch).
    *   **macOS**: `brew install ffmpeg`.

## Usage

1.  **Prepare your files**: Place your MP3 files in a folder.
2.  **Create an order file**: Create a text file (e.g., `chapters.txt`) listing the files in the desired order.
    *   Format: `filename.mp3|Chapter Title`
    *   Or simpler: `filename.mp3` (uses filename as title)

    Example `chapters.txt`:
    ```text
    01_Intro.mp3|Introduction
    02_Story.mp3|The Story Begins
    03_End.mp3
    ```
3.  **Run the script**:

    ```bash
    python m4b-joiner.py "path/to/mp3_folder" "path/to/chapters.txt" "output_book.m4b"
    ```

    **Optional Arguments**:
    *   `-v`, `--verbose`: Enable detailed output (file analysis, parameters).

    **Example**:
    ```bash
    python m4b-joiner.py . chapters.txt my_audiobook.m4b -v
    ```

## Notes

- The script **enforces** that all input MP3s have the same sample rate and channel count. If a mismatch is found, the script will exit with an error to prevent creating a corrupted file.
- Special characters in filenames are handled, but using simple filenames is always safer.

## License

This project is licensed under the terms of the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.
