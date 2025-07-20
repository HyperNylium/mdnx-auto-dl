"""
intel:
ffmpeg -hwaccel qsv -i output_raw.mkv -map 0 -c:v hevc_qsv -preset 7 -global_quality 26 -c:a copy -c:s copy output_hevc_qsv.mkv

AMD:
ffmpeg -hwaccel vaapi -i output_raw.mkv -map 0 -vf format=nv12,hwupload -c:v hevc_vaapi -qp 26 -c:a copy -c:s copy output_hevc_vaapi.mkv

CPU:
ffmpeg -i output_raw.mkv -map 0 -c:v libx265 -preset slow -crf 26 -c:a copy -c:s copy output_hevc_cpu.mkv

Will be setting up an IGPU passthrough LXC container sometime soon to test this.
Will require the "/dev/dri:/dev/dri" bind mount in the compose file.
"""