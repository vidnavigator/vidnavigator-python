import os
from vidnavigator import VidNavigatorClient, VidNavigatorError
import dotenv

dotenv.load_dotenv()


def main():
    """Runs a comprehensive test of the VidNavigator Python SDK."""
    api_key = os.getenv("VIDNAVIGATOR_API_KEY")
    if not api_key:
        print("❌ Error: Please set your VIDNAVIGATOR_API_KEY as an environment variable.")
        print("Example: export VIDNAVIGATOR_API_KEY='your_key_here'")
        return

    client = VidNavigatorClient(api_key=api_key)
    print("🚀 Starting VidNavigator SDK Test\n")

    # --- 1. Health Check ---
    print("--- 1. Health Check ---")
    try:
        health = client.health_check()
        print(f"✅ API Status: {health.get('status')}")
        print(f"📝 Message: {health.get('message')}")
        print(f"🔢 Version: {health.get('version')}")
    except VidNavigatorError as e:
        print(f"❌ Health check failed: {e}")
    print("-" * 25 + "\n")

    # --- 2. Usage Statistics ---
    print("--- 2. Usage Statistics ---")
    try:
        usage_resp = client.get_usage()
        usage_data = usage_resp.data
        
        print("✅ Usage data retrieved:")
        # Subscription
        sub = usage_data.subscription
        print(f"  - Plan: {sub.plan_name} ({sub.interval})")
        if sub.status:
            print(f"  - Subscription status: {sub.status}")
        if sub.cancel_at_period_end is not None:
            print(f"  - Cancels at period end: {sub.cancel_at_period_end}")
        
        # Periods
        up = usage_data.usage_period
        bp = usage_data.billing_period
        print(f"  - Usage period:   {up.start} → {up.end}")
        bp_interval = f" ({bp.interval})" if getattr(bp, 'interval', None) else ""
        print(f"  - Billing period: {bp.start} → {bp.end}{bp_interval}")
        
        # Generated at
        if usage_data.generated_at:
            print(f"  - Generated at:   {usage_data.generated_at}")
        
        # Storage
        print("\n  Storage:")
        storage = usage_data.storage
        print(f"    - Used: {storage.used_formatted} of {storage.limit_formatted} ({storage.percentage:.1f}%)")

        # API Usage
        print("\n  API Usage:")
        for service_name, service_usage in usage_data.usage.model_dump().items():
            if service_usage:
                unit = service_usage.get('unit', 'requests')
                print(f"    - {service_name.replace('_', ' ').title()}: {service_usage['used']:,} / {service_usage['limit']} {unit}")

    except VidNavigatorError as e:
        print(f"⚠️  Could not retrieve usage data: {e}")
    print("-" * 25 + "\n")

    # --- 3. Video Transcript Test ---
    print("--- 3. Video Transcript Test ---")
    test_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"📺 Getting transcript for: {test_video_url}")
    try:
        resp = client.get_transcript(video_url=test_video_url)
        video_info = resp.data.video_info
        transcript = resp.data.transcript

        print("✅ Video Info Retrieved:")
        print(f"  📛 Title: {video_info.title}")
        print(f"  📺 Channel: {video_info.channel}")
        print(f"  ⏱️  Duration: {video_info.duration} seconds")
        
        print("\n📝 First 3 transcript segments:")
        for segment in transcript[:3]:
            print(f"  - [{segment.start:.2f}s - {segment.end:.2f}s]: {segment.text}")

        # --- How to get dicts or JSON ---
        print("\n💡 Tip: The response objects are Pydantic models.")
        print("You can easily convert them to dictionaries or JSON.")

        # Example: Convert the first segment to a dictionary
        first_segment_dict = transcript[0].model_dump()
        print("\n🔄 First segment as a dictionary:")
        print(first_segment_dict)

        # Example: Get the whole response as a JSON string
        print("\n🔄 Full response as pretty-printed JSON (first 300 chars):")
        full_response_json = resp.model_dump_json(indent=2)
        print(full_response_json[:300] + "...")
            
    except VidNavigatorError as e:
        print(f"❌ Transcript error: {e}")
    print("-" * 25 + "\n")

    # --- 4. Video Analysis Test ---
    print("--- 4. Video Analysis Test ---")
    try:
        analysis_resp = client.analyze_video(
            video_url=test_video_url,
            query="What is the main message of this song?"
        )
        analysis = analysis_resp.data.transcript_analysis
        print("✅ Analysis completed:")
        if analysis.summary:
            print(f"📝 Summary: {analysis.summary[:200]}...")
        if analysis.query_answer:
            print(f"💡 Query Answer: {analysis.query_answer}")

    except VidNavigatorError as e:
        print(f"❌ Analysis error: {e}")
    print("-" * 25 + "\n")

    # --- 5. List Uploaded Files ---
    print("--- 5. List Uploaded Files ---")
    try:
        files_resp = client.get_files(limit=5)
        files_data = files_resp.data
        print("✅ Files retrieved:")
        print(f"📊 Total files: {files_data.total_count}")
        print(f"📁 Files returned: {len(files_data.files)}")
        
        if files_data.files:
            print("\n📄 Recent files:")
            for file in files_data.files:
                size_mb = f"{(file.size / 1024 / 1024):.2f} MB" if file.size else "N/A"
                print(f"  - {file.name} ({file.status}) - Size: {size_mb}")
        else:
            print("📭 No files uploaded yet.")
    except VidNavigatorError as e:
        print(f"❌ Files list error: {e}")
    print("-" * 25 + "\n")
    
    print("🎉 SDK Test completed successfully!")
    print("\n💡 Next steps:")
    print("  - Try uploading a file with: client.upload_file(file_path='./your-file.mp4')")
    print("  - Search through your files with: client.search_files(query='your search term')")
    print("  - Analyze uploaded files with: client.analyze_file(file_id='your-file-id')")


if __name__ == "__main__":
    main()