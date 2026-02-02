"""Quick test to verify OpenAI API key works."""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("="*60)
print("Testing OpenAI API Connection")
print("="*60)

# Check API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("\n❌ OPENAI_API_KEY not set!")
    print("\nPlease set it:")
    print("  1. Create .env file with: OPENAI_API_KEY=sk-...")
    print("  2. Or export: export OPENAI_API_KEY=sk-...")
    sys.exit(1)

print(f"\n✅ API key found: {api_key[:10]}...{api_key[-4:]}")

# Test OpenAI client
print("\n📡 Testing connection to OpenAI...")

try:
    import openai
    
    client = openai.OpenAI(api_key=api_key)
    
    # Simple test
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello! API is working.' in exactly 5 words."}
        ],
        max_tokens=20,
        temperature=0
    )
    
    result = response.choices[0].message.content
    
    print(f"\n✅ Connection successful!")
    print(f"📝 Response: {result}")
    print(f"💰 Tokens used: {response.usage.total_tokens}")
    print(f"💸 Cost: ~${response.usage.total_tokens * 0.0000003:.6f}")
    
    print("\n" + "="*60)
    print("✅ API Key Is Working!")
    print("="*60)
    print("\nYou're ready to run experiments:")
    print("  ./setup_and_run.sh")
    print("  or")
    print("  python run_milestone2_deviation.py")
    
except openai.AuthenticationError:
    print("\n❌ Authentication Error!")
    print("Your API key is invalid or expired.")
    print("Please check your key at: https://platform.openai.com/api-keys")
    sys.exit(1)
    
except openai.RateLimitError:
    print("\n⚠ Rate Limit Error!")
    print("You've hit the rate limit. Wait a moment and try again.")
    sys.exit(1)
    
except openai.APIError as e:
    print(f"\n❌ OpenAI API Error: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
