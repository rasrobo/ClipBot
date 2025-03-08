#!/usr/bin/env python3
"""
ClipBot: Automated Video Clip Generator
https://github.com/rasrobo/ClipBot

Automatically creates engaging video clips from vacation photos and videos.
"""

import os
import sys
import argparse
import pickle
import time
import logging
import requests
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# Video processing imports
from scenedetect import open_video, SceneManager, ContentDetector
from scenedetect.scene_detector import SceneList
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
from moviepy.video.fx.all import fadein, fadeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ClipBot')

# Supported video formats
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.wmv')
# Supported audio formats
AUDIO_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.aac')

MUSIC_URLS = [
    "https://cdn.pixabay.com/audio/2024/ambient/24-125766.mp3",  # Instrumental
    "https://cdn.pixabay.com/audio/2024/upbeat/24-127891.mp3",   # Positive vibe
    "https://cdn.pixabay.com/audio/2024/cinematic/24-129345.mp3" # Emotional
]

def download_background_music(music_dir: str) -> None:
    """Download free background music tracks for use in clips."""
    music_dir = Path(music_dir)
    music_dir.mkdir(exist_ok=True)
    
    for i, url in enumerate(MUSIC_URLS):
        output_path = music_dir / f"track_{i+1}.mp3"
        
        # Skip if file already exists
        if output_path.exists():
            logger.info(f"Music file already exists: {output_path}")
            continue
            
        try:
            logger.info(f"Downloading music track {i+1}...")
            response = requests.get(url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Downloaded {output_path}")
        except Exception as e:
            logger.error(f"Failed to download track from {url}: {e}")

def get_cache_path(video_path: str) -> str:
    """Generate a cache file path for a given video."""
    video_path = os.path.abspath(video_path)
    cache_dir = os.path.join(os.path.dirname(video_path), '.clipbot_cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create a filename based on the video path and last modification time
    video_stat = os.stat(video_path)
    cache_filename = f"{os.path.basename(video_path)}_{video_stat.st_mtime:.0f}.pkl"
    return os.path.join(cache_dir, cache_filename)

def detect_scenes(video_path: str, threshold: float = 27.0, use_cache: bool = True) -> SceneList:
    """Detect scenes in a video with caching for consistent results."""
    cache_path = get_cache_path(video_path)
    
    # Check if cached results exist and are valid
    if use_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                logger.info(f"Using cached scene detection results for {os.path.basename(video_path)}")
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached scenes: {e}")
    
    # Perform scene detection
    logger.info(f"Detecting scenes in {os.path.basename(video_path)}...")
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    
    # Cache the results
    if use_cache:
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(scene_list, f)
            logger.info(f"Cached scene detection results to {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to cache scenes: {e}")
    
    return scene_list

def process_audio(video_clip: VideoFileClip, music_clip: Optional[AudioFileClip], volume: float = 0.2, mute_original: bool = False) -> CompositeAudioClip:
    """Blend audio using industry-standard levels (-18dB to -22dB for music)"""
    
    # If there is no audio track just return the music track or None
    if video_clip.audio is None:
        if music_clip:
            music_audio = music_clip.volumex(volume).audio_normalize(-20)
            return music_audio
        else:
            return None
            
    # Normalize original audio to -12dB LUFS for dialogue
    if not mute_original:
        original_audio = video_clip.audio.audio_normalize(-12)
    else:
        original_audio = None
    
    # Process Music
    if music_clip:
        # Set music to 15-25% volume (≈-18dB to -22dB)
        music_audio = music_clip.volumex(volume).audio_normalize(-20)
        
        # Apply high-pass filter to reduce frequency conflict
        music_audio = music_audio.audio_fx(
            afilter="highpass=f=200",
            colors=False
        )
    else:
        music_audio = None
    
    # Compress voice for consistency (if present)
    if not mute_original:
        original_audio = original_audio.audio_fx(
            afilter="compand=0.3|0.6:6:-70/-50/-20:6:0:-90:0.2",
            colors=False
        )
    
    # Mix audio streams
    audio_clips = []
    if original_audio:
        audio_clips.append(original_audio.audio_fadeout(0.5).audio_fadein(0.5).volumex(0.8 if mute_original else 1.0))
    if music_audio:
        audio_clips.append(music_audio.audio_fadeout(0.5).audio_fadein(0.5).volumex(0.2 if not mute_original else 1.0))

    if audio_clips:
        final_audio = CompositeAudioClip(audio_clips)
    else:
        final_audio = None
    
    return final_audio

def process_video(
    video_path: str, 
    output_dir: str,
    max_clip: float = 12.0,
    fade: float = 0.5,
    music_path: Optional[str] = None,
    mute_original: bool = False,
    volume: float = 0.2,
    resolution: Tuple[int, int] = (1280, 720),
    threshold: float = 27.0,
    use_cache: bool = True
) -> List[str]:
    """Process a single video into multiple clips."""
    output_files = []
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # Detect scenes
    scene_list = detect_scenes(video_path, threshold, use_cache)
    
    if not scene_list:
        logger.warning(f"No scenes detected in {video_path}")
        return output_files
    
    logger.info(f"Detected {len(scene_list)} scenes in {os.path.basename(video_path)}")
    
    # Load background music if specified
    music_clip = None
    if music_path and os.path.exists(music_path):
        try:
            music_clip = AudioFileClip(music_path)
            logger.info(f"Loaded background music: {os.path.basename(music_path)}")
        except Exception as e:
            logger.error(f"Failed to load music file {music_path}: {e}")
            music_clip = None
    
    # Process each scene
    for i, scene in enumerate(scene_list):
        output_path = os.path.join(output_dir, f"{base_name}_clip{i+1}.mp4")
        
        # Skip if output already exists
        if os.path.exists(output_path) and use_cache:
            logger.info(f"Clip already exists: {os.path.basename(output_path)}")
            output_files.append(output_path)
            continue
        
        try:
            # Extract scene timing
            start_time = scene[0].get_seconds()
            end_time = scene[1].get_seconds()
            
            # Skip scenes that are too short
            if end_time - start_time < 1.0:
                logger.debug(f"Skipping scene {i+1} (too short: {end_time - start_time:.2f}s)")
                continue
                
            # Enforce maximum clip duration
            if end_time - start_time > max_clip:
                end_time = start_time + max_clip
            
            logger.info(f"Processing scene {i+1}: {start_time:.2f}s to {end_time:.2f}s")
            
            # Extract the clip
            video_clip = VideoFileClip(video_path).subclip(start_time, end_time)
            
            # Apply fade effects
            fade_duration = min(fade, video_clip.duration / 4)  # Ensure fade isn't too long
            video_clip = fadein(video_clip, fade_duration)
            video_clip = fadeout(video_clip, fade_duration)
            
            # Handle audio
            final_audio = process_audio(video_clip, music_clip, volume, mute_original)
            if final_audio:
                video_clip = video_clip.set_audio(final_audio)
            else:
                video_clip = video_clip.without_audio()
            
            # Resize to target resolution if needed
            if resolution and (video_clip.w != resolution[0] or video_clip.h != resolution[1]):
                video_clip = video_clip.resize(resolution)
            
            # Write the output file
            video_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                threads=4,
                preset='medium'
            )
            
            # Clean up
            video_clip.close()
            
            logger.info(f"Created clip: {os.path.basename(output_path)}")
            output_files.append(output_path)
            
        except Exception as e:
            logger.error(f"Error processing scene {i+1}: {e}")
    
    return output_files

def process_directory(
    input_dir: str,
    output_dir: str,
    max_clip: float = 12.0,
    fade: float = 0.5,
    music_path: Optional[str] = None,
    mute_original: bool = False,
    volume: float = 0.2,
    resolution: Tuple[int, int] = (1280, 720),
    threshold: float = 27.0,
    use_cache: bool = True,
    recursive: bool = True
) -> int:
    """Process all videos in a directory, optionally recursively."""
    total_clips = 0
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Walk through the directory
    for root, dirs, files in os.walk(input_dir):
        # Process video files
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                video_path = os.path.join(root, file)
                
                # Create relative output path to maintain directory structure
                if recursive:
                    rel_path = os.path.relpath(root, input_dir)
                    clip_output_dir = os.path.join(output_dir, rel_path)
                else:
                    clip_output_dir = output_dir
                
                # Process the video
                clips = process_video(
                    video_path=video_path,
                    output_dir=clip_output_dir,
                    max_clip=max_clip,
                    fade=fade,
                    music_path=music_path,
                    mute_original=mute_original,
                    volume=volume,
                    resolution=resolution,
                    threshold=threshold,
                    use_cache=use_cache
                )
                
                total_clips += len(clips)
        
        # Stop if not recursive
        if not recursive:
            break
    
    return total_clips

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='ClipBot: Automated Video Clip Generator')
    
    # Required arguments
    parser.add_argument('input_dir', help='Source media folder')
    parser.add_argument('output_dir', help='Processed clips folder')
    
    # Optional arguments
    parser.add_argument('--max-clip', type=float, default=12.0,
                        help='Maximum clip duration in seconds (default: 12.0)')
    parser.add_argument('--fade', type=float, default=0.5,
                        help='Fade duration in seconds (default: 0.5)')
    parser.add_argument('--music', type=str,
                        help='Background music file path')
    parser.add_argument('--download-music', action='store_true',
                        help='Download free background music tracks')
    parser.add_argument('--mute', action='store_true',
                        help='Remove original audio')
    parser.add_argument('--volume', type=float, default=0.2,
                        help='Music volume (0.0-1.0)')
    parser.add_argument('--resolution', type=str, default='720p',
                        choices=['480p', '720p', '1080p', 'original'],
                        help='Output resolution (default: 720p)')
    parser.add_argument('--threshold', type=float, default=27.0,
                        help='Scene detection threshold (default: 27.0)')
    parser.add_argument('--no-cache', action='store_true',
                        help='Disable caching for scene detection')
    parser.add_argument('--non-recursive', action='store_true',
                        help='Process only the top-level directory')
    
    args = parser.parse_args()
    
    # Convert resolution to dimensions
    if args.resolution == 'original':
        resolution = None
    else:
        res_map = {
            '480p': (854, 480),
            '720p': (1280, 720),
            '1080p': (1920, 1080)
        }
        resolution = res_map[args.resolution]
    
    # Download music if requested
    if args.download_music:
        music_dir = os.path.join(args.output_dir, 'background_music')
        download_background_music(music_dir)
        
        # If no specific music file was provided, use the first downloaded track
        if not args.music:
            first_track = os.path.join(music_dir, 'track_1.mp3')
            if os.path.exists(first_track):
                args.music = first_track
                logger.info(f"Using downloaded music track: {first_track}")
    
    # Process the directory
    start_time = time.time()
    total_clips = process_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        max_clip=args.max_clip,
        fade=args.fade,
        music_path=args.music,
        mute_original=args.mute,
        volume=args.volume,
        resolution=resolution,
        threshold=args.threshold,
        use_cache=not args.no_cache,
        recursive=not args.non_recursive
    )
    
    # Report results
    elapsed_time = time.time() - start_time
    logger.info(f"Processing complete! Generated {total_clips} clips in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
