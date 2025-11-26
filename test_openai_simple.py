import os
from openai import AzureOpenAI

# Test content - using realistic technical documentation text
# This simulates what a typical page might contain
test_content = """
TIMKEN

WARNINGS/DISCLAIMERS

A WARNING Failure to observe the following warnings could create a risk of death or serious injury.

Proper maintenance and handling practices are critical. Machine operators must:
• Follow all safety guidelines outlined in the equipment manual
• Wear appropriate personal protective equipment (PPE)
• Ensure all guards and safety devices are in place before operation
• Never bypass safety interlocks or disable emergency stop mechanisms

Installation and Setup Requirements:
1. Verify power supply matches equipment specifications
2. Ensure adequate grounding and electrical safety
3. Check all mechanical connections for proper torque
4. Inspect hydraulic and pneumatic systems for leaks
5. Calibrate sensors and measurement devices according to manufacturer specifications

Maintenance Schedule:
- Daily: Visual inspection of critical components
- Weekly: Lubrication of moving parts
- Monthly: Complete system inspection and testing
- Annually: Major service and component replacement as needed

For technical support or questions regarding operation, contact:
Technical Support Line: 1-800-XXX-XXXX
Email: support@example.com
Website: www.example.com/technical-support
"""

# Initialize OpenAI client
endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
api_key = os.environ.get("AZURE_OPENAI_API_KEY")
deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

if not endpoint or not deployment:
    print("❌ Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT must be set")
    exit(1)

print(f"🔧 OpenAI Configuration:")
print(f"   Endpoint: {endpoint}")
print(f"   Deployment: {deployment}")
print(f"   API Version: 2025-01-01-preview")
print(f"   Test content length: {len(test_content)} characters\n")

client = AzureOpenAI(
    api_key=api_key,
    api_version="2025-01-01-preview",
    azure_endpoint=endpoint,
)

# Test with the same prompt used in production
prompt = """You are a helpful assistant that summarizes technical documentation.
Provide a clear and concise summary of the following page content in 2-3 sentences."""

print("📤 Sending request to Azure OpenAI...\n")

try:
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": test_content},
        ],
        max_completion_tokens=512,
    )
    
    print("✅ Response received successfully!\n")
    print("=" * 80)
    print("FULL RESPONSE DETAILS:")
    print("=" * 80)
    print(f"Response ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Created: {response.created}")
    print(f"Number of choices: {len(response.choices)}")
    print()
    
    if response.choices:
        choice = response.choices[0]
        print(f"Choice 0:")
        print(f"  Finish reason: {choice.finish_reason}")
        print(f"  Message role: {choice.message.role}")
        print(f"  Message content type: {type(choice.message.content)}")
        print(f"  Message content is None: {choice.message.content is None}")
        print(f"  Message content length: {len(choice.message.content) if choice.message.content else 0}")
        print(f"  Message content repr: {repr(choice.message.content)[:500]}")
        print()
        
        # Check for content filter
        if hasattr(choice, 'content_filter_results'):
            print(f"  Content filter results: {choice.content_filter_results}")
        if hasattr(response, 'prompt_filter_results'):
            print(f"  Prompt filter results: {response.prompt_filter_results}")
    
    # Check usage
    if hasattr(response, 'usage') and response.usage:
        print(f"\nToken usage:")
        print(f"  Prompt tokens: {response.usage.prompt_tokens}")
        print(f"  Completion tokens: {response.usage.completion_tokens}")
        print(f"  Total tokens: {response.usage.total_tokens}")
    
    print("=" * 80)
    
    # Extract summary
    summary = response.choices[0].message.content
    if summary:
        print(f"\n✅ SUMMARY ({len(summary)} chars):")
        print(summary)
    else:
        print("\n⚠️ WARNING: EMPTY SUMMARY RETURNED!")
        print("This confirms the issue - OpenAI is returning an empty/null content field.")
        print("\nPossible causes:")
        print("1. Content filter blocking the response")
        print("2. Model deployment configuration issue")
        print("3. API version compatibility problem")
        print("4. Token limits or quota issues")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
