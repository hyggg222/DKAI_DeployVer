# DK_AI Deployment

This is the standalone deployment version of the DK_AI project.

## Overview
This folder contains the complete standalone server and necessary components to run the AI system without external complex dependencies.

## Installation
1.  Install Python 3.10+
2.  Install requirements:
    ```bash
    pip install -r requirements.txt
    ```

## Usage
Run the server:
```bash
python ai_server.py
```

## Structure
- `ai_server.py`: Main server entry point.
- `mobile_flutter/`: Mobile application source.
- `src/`: Source code for detectors and logic.
- `weights/`: AI models.
