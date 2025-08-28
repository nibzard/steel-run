"""
Example usage of Twitter actions with Steel.run.

This example demonstrates how to use the TwitterPostAction and TwitterReplyAction
to automate Twitter interactions using Claude Computer Use.
"""

import asyncio
import os
from app.actions.twitter import TwitterPostAction, TwitterReplyAction


async def example_post_tweet():
    """Example: Post a tweet to Twitter."""
    print("🐦 Twitter Post Example")
    print("=" * 50)
    
    # Create action instance
    action = TwitterPostAction()
    
    # Prepare parameters
    message = "Hello from Steel.run! 🚀 Automating Twitter with AI-powered web actions."
    credentials = {
        "username": os.getenv("TWITTER_USERNAME", "your_username"),
        "password": os.getenv("TWITTER_PASSWORD", "your_password")
    }
    
    try:
        # Execute the action
        print(f"Posting tweet: '{message}'")
        print("Executing Twitter post action...")
        
        result = await action.execute_safely(
            message=message,
            credentials=credentials,
            wait_for_confirmation=True
        )
        
        # Display results
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Execution time: {result['execution_time_ms']}ms")
        
        if result['status'] == 'success':
            print("✅ Tweet posted successfully!")
            
            data = result.get('data', {})
            print(f"Tweet message: {data.get('tweet_message')}")
            print(f"Message length: {data.get('message_length')} characters")
            print(f"Final URL: {data.get('final_url')}")
            
            if result.get('screenshot'):
                print("📸 Screenshot captured for verification")
        else:
            print("❌ Tweet posting failed")
            print(f"Error code: {result.get('error_code')}")
            
    except Exception as e:
        print(f"❌ Error executing Twitter post action: {e}")


async def example_reply_to_tweet():
    """Example: Reply to a tweet on Twitter."""
    print("\n🐦 Twitter Reply Example")
    print("=" * 50)
    
    # Create action instance
    action = TwitterReplyAction()
    
    # Prepare parameters
    tweet_url = "https://x.com/elonmusk/status/1234567890123456789"  # Replace with actual tweet
    reply_message = "Great point! Thanks for sharing this insight. 💡"
    credentials = {
        "username": os.getenv("TWITTER_USERNAME", "your_username"),
        "password": os.getenv("TWITTER_PASSWORD", "your_password")
    }
    
    try:
        # Execute the action
        print(f"Replying to tweet: {tweet_url}")
        print(f"Reply message: '{reply_message}'")
        print("Executing Twitter reply action...")
        
        result = await action.execute_safely(
            tweet_url=tweet_url,
            reply_message=reply_message,
            credentials=credentials
        )
        
        # Display results
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Execution time: {result['execution_time_ms']}ms")
        
        if result['status'] == 'success':
            print("✅ Reply posted successfully!")
            
            data = result.get('data', {})
            print(f"Original tweet: {data.get('original_tweet_url')}")
            print(f"Reply message: {data.get('reply_message')}")
            print(f"Reply length: {data.get('reply_length')} characters")
            
            if result.get('screenshot'):
                print("📸 Screenshot captured for verification")
        else:
            print("❌ Reply posting failed")
            print(f"Error code: {result.get('error_code')}")
            
    except Exception as e:
        print(f"❌ Error executing Twitter reply action: {e}")


async def example_action_metadata():
    """Example: Display action metadata and capabilities."""
    print("\n📋 Twitter Actions Metadata")
    print("=" * 50)
    
    # Get metadata for both actions
    post_action = TwitterPostAction()
    reply_action = TwitterReplyAction()
    
    for action in [post_action, reply_action]:
        metadata = action.get_metadata()
        
        print(f"\n🎯 Action: {metadata['name']}")
        print(f"Description: {metadata['description']}")
        print(f"Category: {metadata['category']}")
        print(f"Tags: {', '.join(metadata['tags'])}")
        print(f"Requires Auth: {metadata['requires_auth']}")
        print(f"Timeout: {metadata['timeout_seconds']}s")
        print(f"Estimated Duration: {metadata['estimated_duration_seconds']}s")
        print(f"Success Rate Threshold: {metadata['success_rate_threshold']}")
        
        print("\nParameters:")
        for param_name, param_config in metadata['parameters'].items():
            required = "✓" if param_config.get('required', False) else "○"
            print(f"  {required} {param_name} ({param_config.get('type', 'unknown')})")
            if param_config.get('description'):
                print(f"    {param_config['description']}")


async def main():
    """Run all Twitter action examples."""
    print("🚀 Steel.run Twitter Actions Examples")
    print("=====================================")
    
    # Display action metadata
    await example_action_metadata()
    
    # Note: These examples require actual Twitter credentials
    # and will perform real actions on Twitter
    print("\n⚠️  Note: The following examples require Twitter credentials")
    print("Set TWITTER_USERNAME and TWITTER_PASSWORD environment variables")
    print("WARNING: These will perform real actions on your Twitter account!")
    
    # Uncomment to run actual Twitter actions
    # await example_post_tweet()
    # await example_reply_to_tweet()
    
    print("\n✨ Examples completed!")
    print("\nTo run actual Twitter actions:")
    print("1. Set TWITTER_USERNAME and TWITTER_PASSWORD environment variables")
    print("2. Set STEEL_API_KEY and ANTHROPIC_API_KEY environment variables")
    print("3. Uncomment the action calls in main()")
    print("4. Replace the example tweet URL with a real one")


if __name__ == "__main__":
    asyncio.run(main())