#!/usr/bin/env python3
"""
DKAI Test Server Runner
Runs the unified DKAI monitoring server in file simulation mode (looping test_videos/).
"""
import os
import sys

# Ensure mode is test/file
os.environ.setdefault("VIDEO_SOURCE", "file")

if __name__ == "__main__":
    from ai_server import main
    main()
