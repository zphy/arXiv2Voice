# arXiv2Voice

Utility to convert a given arXiv number into audio, so that one can listen to the contents on the go.

## Prerequisites

Install packages latex2rtf, striprtf, urllib before using this code. The latter two can be installed with "pip install -r requirements.txt" in the main directory. latex2rtf can be found at http://latex2rtf.sourceforge.net. This code is currently only compatible with Mac OS.

## Usage example

Run a command of the form "python Paper2Voice.py 1907.10066" on the command line. It will generate an mp3 file in the output folder.

## Options

-r, --rate: set rate of speech. Example: "python Paper2Voice.py 1907.10066 -r 200"
--si: having this flag includes supplementary information

## Contributing

Feel free to contact the author with any questions or requests.

## Authors

Harry Zhou - (https://lukin.physics.harvard.edu/people/hangyun-harry-zhou)

## License

This project is licensed under the GNU GPL v3 License - see the [LICENSE.md](LICENSE.md) file for details
