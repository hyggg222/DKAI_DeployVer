# Changelog

All notable changes to the DKAI project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-12

### Added
- Unified dual-mode architecture supporting both live RTSP streaming and looping test video files via `VIDEO_SOURCE` environment variable.
- Staff confirmation endpoint (`POST /api/ingest/confirm`) to allow parking staff to review and confirm flagged license plate reads.
- Confirmation archive endpoint (`GET /api/ingest/history`) for querying verified vehicle records.
- Automated test suite in `tests/` covering database operations, vehicle detection bounding box geometry, module imports, and API routes.
- Fallback image placeholders (`static/no_plate.jpg`, `static/no_car.jpg`) with recursive loop prevention (`this.onerror=null`).
- Interactive demo runner scripts (`run_demo.bat` and `run_demo.ps1`) for launching dashboard and mobile app with simulated triggers.

### Changed
- English localization across all web dashboard components and labels.
- Synchronized port `8001` across Dockerfile, docker-compose, server configuration, and Flutter client.
- Database path configurable via `DATABASE_PATH` environment variable with proper persistent volume mounting in Docker Compose.
- Dynamic weight resolution in `CarDetector` targeting bundled `weights/yolo11s.pt`.

### Fixed
- Fixed 404 infinite recursion loop on dashboard caused by missing fallback image assets.
- Fixed Docker database persistence bug where `docker-compose.yml` mounted an unread database file.
- Removed hardcoded developer paths from `src/vehicle_detector.py`.
- Removed tracked Gradle build problem reports from Git repository.

## [1.0.0] - 2026-01-10

### Added
- Initial release of DKAI vehicle access management system.
- Real-time vehicle detection with YOLOv11.
- License plate localization with custom fine-tuned YOLO model.
- OCR text extraction and validation powered by Google Gemini 2.0 Flash.
- Dual camera stream support (entry plate capture and rear vehicle access).
- Real-time WebSocket event broadcasting with Socket.IO.
- Flutter mobile companion app for remote monitoring and staff review.
- SQLite logging with write-ahead logging (WAL) mode for concurrent access.
