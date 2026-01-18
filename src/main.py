"""
main script to be run
"""

import os
import yaml
import ffmpeg
import numpy as np
import sys
sys.path.insert(0, ".")
from src.videos_conversion import convert_and_concatenate_mp4_to_avi, avi_to_mp4
from src.data_moshing import mosh_data

FPS=30

def main() -> None:

    parameters = yaml.safe_load(open("parameters.yaml", "r"))
    paths = parameters["paths"]

    videos_path = get_videos_path(paths["input_folder"])
    assert videos_path, f"No mp4 videos inside {paths["input_folder"]} were found"

    #videos_length = [get_video_length(video_path) for video_path in videos_path]
    #video_change_seconds = np.cumsum(videos_length).tolist()

    in_path = paths["temp_original_vid_path"]
    out_path = paths["temp_moshed_vid_path"]
    failure, change_times = convert_and_concatenate_mp4_to_avi(videos_path, in_path)
    print("The videos conversion if finished, proceeding to the moshing")
    change_times = detect_scene_changes(in_path)

    # get between videos moshing_intervals
    in_between_videos_moshing_intervals = get_in_between_videos_moshing_intervals(change_times, offset=1.5)

    moshing_intervals: list[list[int]] = []
    moshing_intervals.extend(in_between_videos_moshing_intervals)
    #moshing_intervals.extend(parameters["settings"]["manual_moshing_intervals"])

    mosh_data(in_path, out_path, moshing_intervals, parameters["settings"]["repeat_p_frames"])

    avi_to_mp4(out_path, paths["output_video_path"])
    
    # gets rid of the in-between files
    #os.remove(paths["temp_original_vid_path"])
    #os.remove(paths["temp_moshed_vid_path"])

def get_videos_path(path:str="data") -> list[str]:
    """videos have to be mp4 and have mp4 extension"""
    
    videos_path: list[str] = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            if filename.endswith(".mp4"):
                videos_path.append(
                    os.path.join(root, filename)
                )
    return videos_path

def get_in_between_videos_moshing_intervals(video_change_seconds: list[int], offset:int = 0.5) -> list[list[int]]:
    offset *= FPS
    res: list[list[int]] = []
    for video_change_sec in video_change_seconds:
        res.append([video_change_sec-offset, video_change_sec+offset])
    return res

def detect_scene_changes(video_path, threshold=0.1):
    """
    Returns a list of timestamps (in seconds) where significant scene changes occur.
    """
    out, err = ffmpeg.run(
        ffmpeg.input(video_path)
        .filter('select', f'gt(scene,{threshold})')
        .output('null', format='null')
        .global_args('-hide_banner'),
        capture_stdout=True, capture_stderr=True
    )

    timestamps = []
    for line in err.decode().split('\n'):
        if 'pts_time:' in line:
            t = float(line.split('pts_time:')[1].split(' ')[0])
            timestamps.append(round(t, 3))
    return timestamps

import cv2
import numpy as np

def detect_scene_changes(video_path, threshold=40.0):
    cap = cv2.VideoCapture(video_path)
    scene_changes = []
    prev_frame = None
    frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            mean_diff = np.mean(diff)
            if mean_diff > threshold:
                scene_changes.append(frame_index)
        prev_frame = gray
        frame_index += 1

    cap.release()
    return scene_changes


if __name__ == "__main__":
    main()
