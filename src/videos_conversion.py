"""converts videos"""


import ffmpeg
import os

def convert_and_concatenate_mp4_to_avi(input_mp4_paths: list[str], output_avi_path: str) -> tuple[bool, list[float]]:
    if not input_mp4_paths:
        print("Error: No input files provided.")
        return False, []

    for path in input_mp4_paths:
        if not os.path.isfile(path):
            print(f"Error: Input file does not exist: {path}")
            return False, []

    width, height = 480, 854
    fps = 30
    normalized_video_streams = []
    audio_streams = []
    durations = []

    for path in input_mp4_paths:
        input_stream = ffmpeg.input(path)
        video_stream = (
            input_stream.video
            .filter('scale', width, height)
            .filter('setsar', '1')
            .filter('fps', fps=fps)
        )
        audio_stream = input_stream.audio
        normalized_video_streams.append(video_stream)
        audio_streams.append(audio_stream)

        probe = ffmpeg.probe(path)
        durations.append(float(probe['format']['duration']))

    # Flatten streams in correct order: v0,a0,v1,a1,...
    streams = []
    for v, a in zip(normalized_video_streams, audio_streams):
        streams.extend([v, a])

    concat_stream = ffmpeg.concat(*normalized_video_streams, v=1, a=0).node
    video = concat_stream[0]
    audio = concat_stream[1]

    # Compute cumulative change points 
    change_points = [0.0] 
    for d in durations[:-1]: 
        change_points.append(change_points[-1] + d)

    ffmpeg.output(video, output_avi_path, vcodec='mpeg4', acodec='pcm_s16le').overwrite_output().run()
    return True, change_points

def convert_and_concatenate_mp4_to_avi2(input_mp4_paths: list[str], output_avi_path: str) -> tuple[bool, list[float]]:
    if not input_mp4_paths:
        print("Error: No input files provided.")
        return False, []

    for path in input_mp4_paths:
        if not os.path.isfile(path):
            print(f"Error: Input file does not exist: {path}")
            return False, []

    width, height = 480, 854
    fps = 30
    sample_rate = 44100
    channels = 2

    video_streams = []
    audio_streams = []
    durations = []

    for path in input_mp4_paths:
        probe = ffmpeg.probe(path)
        duration = float(probe['format']['duration'])
        durations.append(duration)

        has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])

        # Always process video
        video = (
            ffmpeg.input(path)
            .video
            .filter('scale', width, height)
            .filter('setsar', '1')
            .filter('fps', fps=fps)
        )
        video_streams.append(video)

        if has_audio:
            # Normalize real audio
            audio = (
                ffmpeg.input(path)
                .audio
                .filter('aresample', sample_rate)
                .filter('pan', 'stereo|c0=c0|c1=c1')  # ensure stereo
            )
            audio_streams.append(audio)
        else:
            # Generate silent audio as a separate lavfi input
            silent = ffmpeg.input(
                f'anullsrc=r={sample_rate}:cl=stereo',
                format='lavfi',
                t=duration
            ).audio
            audio_streams.append(silent)

    # Now build concat: interleave video and audio streams
    # But note: silent audio comes from separate inputs!
    # So we must collect all inputs used
    inputs = []
    streams_for_concat = []

    for i in range(len(input_mp4_paths)):
        # Each video comes from input_mp4_paths[i]
        # Each audio may come from either the same file or a lavfi source
        # We already have video_streams[i] and audio_streams[i] as nodes
        streams_for_concat.extend([video_streams[i], audio_streams[i]])

    # Now concat
    concat_node = ffmpeg.concat(*streams_for_concat, v=1, a=1)

    # DO NOT index with [0], [1] — use named outputs or pass directly
    # Instead, just feed into output using the node's outputs
    # concat_node has 'v' and 'a' outputs
    try:
        ffmpeg.output(
            concat_node['v'],
            concat_node['a'],
            output_avi_path,
            vcodec='mpeg4',
            acodec='pcm_s16le',
            ar=sample_rate,
            ac=channels
        ).overwrite_output().run()
    except ffmpeg.Error as e:
        print("FFmpeg error:", e.stderr.decode() if e.stderr else str(e))
        return False, []

    # Compute change points
    change_points = [0.0]
    for d in durations[:-1]:
        change_points.append(change_points[-1] + d)

    return True, change_points



def avi_to_mp4(input_path: str, output_path: str) -> bool:
    
    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vcodec="libx264",   # H.264 video codec
                acodec="aac",       # AAC audio codec
                crf=30,#10,#23,             # Quality level (lower = better)
                preset="medium",    # Speed/quality tradeoff
                movflags="+faststart"  # Web-friendly MP4 playback
            )
            .overwrite_output()
            .run(quiet=False)
        )

        print(f"✅ Successfully converted to MP4: {output_path}")
        return True

    except ffmpeg.Error as e:
        print("❌ FFmpeg error:", e.stderr.decode() if e.stderr else str(e))
        return False
    except Exception as e:
        print("❌ Unexpected error:", e)
        return False
