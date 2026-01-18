"""includes function that performs the datamoshing"""

import math


fps = 30
start_sec = 1
end_sec = 10
repeat_p_frames = 2 #15

def mosh_data(input_avi_path:str, output_avi_path:str, moshing_intervals: list[list[float]], repeat_p_frames: int) -> None:
    """
    performs the datamosh, taken from this github script:
    https://github.com/happyhorseskull/you-can-datamosh-on-linux/blob/master/do_the_mosh.py
    """

    # smooth repetition function (sine-based)
    def smooth_repeat(idx_in_window: int, base: int, amplitude: int, total_window: int) -> int:
        """Return smooth variable repeat count across the mosh window."""
        t = idx_in_window / total_window  # normalized position (0 → 1)
        # oscillate between (base - amplitude) and (base + amplitude)
        val = base + int(math.sin(math.pi * t) * amplitude)
        return max(1, val)

    # open up the new files so we can read and write bytes to them
    in_file  = open(input_avi_path,  'rb')
    out_file = open(output_avi_path, 'wb')

    # because we used 'rb' above when the file is read the output is in byte format instead of Unicode strings
    in_file_bytes = in_file.read()

    # 0x30306463 which is ASCII 00dc signals the end of a frame. '0x' is a common way to say that a number is in hexidecimal format.
    frames = in_file_bytes.split(bytes.fromhex('30306463'))

    # 0x0001B0 signals the beginning of an i-frame. Additional info: 0x0001B6 signals a p-frame
    iframe = bytes.fromhex('0001B0')

    # We want at least one i-frame before the glitching starts
    i_frame_yet = False
    

    for index, frame in enumerate(frames):

        is_not_in_any_interval = not any(start <= index <= stop for start, stop in moshing_intervals)
        if  i_frame_yet == False or is_not_in_any_interval:
            # the split above removed the end of frame signal so we put it back in
            out_file.write(frame + bytes.fromhex('30306463'))

            # found an i-frame, let the glitching begin
            if frame[5:8] == iframe: i_frame_yet = True

        else:
            # while we're moshing we're repeating p-frames and multiplying i-frames
            if frame[5:8] != iframe:
                # this repeats the p-frame x times
                #for i in range(repeat_p_frames):
                #    out_file.write(frame + bytes.fromhex('30306463'))
                # calculate frame boundaries (approximate, using fps)
                start_frame = index #int(start_sec * fps)
                end_frame = int(start_frame + 30)
                total_window = max(1, end_frame - start_frame)


                # P-frame — apply smooth repetition
                idx_in_window = index - start_frame
                # vary repetition smoothly between base ± 2
                rep_count = smooth_repeat(idx_in_window, base=repeat_p_frames, amplitude=1, total_window=total_window)
                for _ in range(rep_count):
                    out_file.write(frame + bytes.fromhex('30306463'))


    in_file.close()
    out_file.close()





