# vidnavigator-python
Python SDK for the VidNavigator Developer API

## Installation

```bash
pip install git+https://github.com/DeepSearchVideo/vidnavigator-python.git  # or publish on PyPI
```

## Quickstart

```python
from vidnavigator import VidNavigatorClient

client = VidNavigatorClient(api_key="YOUR_API_KEY")

# Health check
print(client.health_check())

# Fetch transcript from YouTube
transcript = client.get_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    language="en",
)
print(transcript)

# AI analysis
analysis = client.analyze_video(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    query="What is the main topic discussed?",
)
print(analysis)

# Remember to close the client (or use `with` statement)
client.close()
```

### Using a Context Manager

```python
from vidnavigator import VidNavigatorClient

with VidNavigatorClient(api_key="YOUR_API_KEY") as client:
    results = client.search_videos(query="best practices for React development")
    print(results)
```

## Development

1. Install dependencies for development:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```
2. Run tests with `pytest`.

## License

This SDK is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
