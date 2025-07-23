# vidnavigator-python
Python SDK for the VidNavigator Developer API

## Installation

```bash
pip install vidnavigator
```

## Quickstart

```python
from vidnavigator import VidNavigatorClient

client = VidNavigatorClient(api_key="YOUR_API_KEY")

# Health check
print(client.health_check())

# Fetch transcript from YouTube
resp = client.get_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
)

# Get data as dictionary
data = resp.data.model_dump()  # We use pydantic for object formatting
print(data['video_info'])  # Get video metadata
print(data['transcript'])  # Get video transcript

# AI analysis
resp = client.analyze_video(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    query="What is the main topic discussed?",
)
analysis = resp.data.transcript_analysis
print(analysis.summary)
print(analysis.query_answer)
```

## Using a Context Manager

```python
from vidnavigator import VidNavigatorClient

with VidNavigatorClient(api_key="YOUR_API_KEY") as vn:
    results = vn.analyze_video(
        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        query="What is the main topic discussed?")
    print(results)
```


## More Examples & Documentation

For a comprehensive set of usage examples covering more SDK features, please see the [`test.py`](https://github.com/vidnavigator/vidnavigator-python/blob/main/test.py)

For full API documentation, visit [docs.vidnavigator.com](https://docs.vidnavigator.com).


## License

This SDK is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
