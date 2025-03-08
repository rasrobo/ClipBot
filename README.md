# ClipBot: Automated Video Clip Generator

ClipBot automates video clip creation from your home videos! Perfect for TikTok, YouTube Shorts, and Instagram Reels. No video editing experience needed!

Easy video clipping for everyone! ClipBot automatically finds and creates engaging clips from your home videos for social media. Try it today!

## Features

- **Automatic Scene Detection**: Intelligently identifies the most engaging moments from your videos
- **Attention Span Optimization**: Creates clips that maintain viewer interest (12-15 seconds by default)
- **Background Music**: Includes free, license-free tracks for your clips
- **Smooth Transitions**: Professional fade-in/fade-out effects between scenes
- **Multi-platform Support**: Process videos in various formats (MP4, MOV, AVI)
- **Batch Processing**: Handle multiple videos recursively through folders
- **Smart Audio Blending**: Automatically adjusts background music volume based on video content
- **Professional Audio Levels**: Implements industry-standard audio mixing practices

## Getting Started

### Installation

```
# Clone the repository
git clone https://github.com/rasrobo/ClipBot.git
cd ClipBot

# Create and activate virtual environment
python -m venv clipbot-env
source clipbot-env/bin/activate  # On Windows: clipbot-env\Scripts\activate

# Install ClipBot
pip install -r requirements.txt
```

### Basic Usage

```
python clipbot.py ~/vacation_media/ output_clips/
```

### Advanced Options

```
python clipbot.py ~/vacation_media/ output_clips/ \
  --max-clip 15 --fade 1.0 --music "summer_vibes.mp3" \
  --volume 0.2 --resolution 1080p --ducking --eq-profile instrumental
```

## Parameters Explained

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--max-clip` | Maximum clip duration in seconds | 12 |
| `--fade` | Fade duration in seconds | 0.75 |
| `--music` | Background music file | None |
| `--volume` | Music volume (0.0-1.0) | 0.2 |
| `--resolution` | Output quality | 720p |
| `--ducking` | Enable voice-activated volume ducking | False |
| `--eq-profile` | EQ profile for background music | None |
| `--normalize-level` | Target LUFS for audio normalization | -14 |

## For Complete Beginners

Never edited a video before? No problem! ClipBot was designed with you in mind:

1. **Simply point to your folder**: Just tell ClipBot where your vacation videos are stored
2. **Let the AI work**: The software automatically detects interesting scenes
3. **Enjoy your clips**: Find professionally edited clips in your output folder

ClipBot handles all the technical aspects of video editing that typically require experience:
- Scene selection
- Proper transitions
- Audio balancing
- Video formatting

## Example Results

ClipBot typically generates 30-40 clips from an hour of raw footage, focusing on the most engaging content. The intelligent scene detection prioritizes:

- Clear, well-lit scenes
- Faces and people
- Action and movement
- Audio peaks (laughter, excited voices)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the open-source community for providing excellent tools and libraries
- Music tracks provided by [Pixabay](https://pixabay.com/music/)

