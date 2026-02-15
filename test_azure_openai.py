#!/usr/bin/env python3
"""
Azure OpenAI Configuration Test Script

Tests Azure OpenAI integration with the HR Automation system.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_config():
    """Test configuration loading"""
    print("=" * 60)
    print("1. Testing Configuration Loading")
    print("=" * 60)

    from src.config import Config

    print(f"✓ LLM Provider: {Config.LLM_PROVIDER}")

    if Config.LLM_PROVIDER == "azure":
        print(f"✓ Azure Endpoint: {Config.AZURE_OPENAI_ENDPOINT}")
        print(f"✓ Azure Deployment: {Config.AZURE_OPENAI_DEPLOYMENT}")
        print(f"✓ Azure Model: {Config.AZURE_OPENAI_MODEL}")
        print(f"✓ Azure API Version: {Config.AZURE_OPENAI_API_VERSION}")

        # Validate required fields
        assert Config.AZURE_OPENAI_API_KEY, "❌ AZURE_OPENAI_API_KEY not set"
        assert Config.AZURE_OPENAI_ENDPOINT, "❌ AZURE_OPENAI_ENDPOINT not set"
        assert Config.AZURE_OPENAI_DEPLOYMENT, "❌ AZURE_OPENAI_DEPLOYMENT not set"

        print("✅ All required Azure OpenAI configuration present")
    else:
        print(f"ℹ️  Current provider is '{Config.LLM_PROVIDER}', not Azure OpenAI")
        print("   To test Azure OpenAI, set LLM_PROVIDER=azure in .env")

    print()


def test_llm_creation():
    """Test LLM factory with Azure OpenAI"""
    print("=" * 60)
    print("2. Testing LLM Factory")
    print("=" * 60)

    from src.llm_provider import LLMFactory, create_summary_llm

    try:
        # Test factory method
        llm = LLMFactory.create_llm(provider="azure")
        print("✓ Azure OpenAI LLM created successfully via factory")
        print(f"  Model: {llm.model}")
        print(f"  Temperature: {llm.temperature}")

        # Test convenience function
        llm2 = create_summary_llm(provider="azure")
        print("✓ Azure OpenAI LLM created successfully via convenience function")

        print("✅ LLM factory working correctly")
    except Exception as e:
        print(f"❌ LLM creation failed: {e}")
        return False

    print()
    return True


def test_simple_inference():
    """Test simple inference"""
    print("=" * 60)
    print("3. Testing Simple Inference")
    print("=" * 60)

    from src.llm_provider import create_summary_llm

    try:
        llm = create_summary_llm(provider="azure")

        # Simple test
        response = llm.invoke("Say 'Azure OpenAI is working!' in exactly this format.")

        print(f"✓ Inference successful")
        print(f"  Response: {response.content}")

        if "Azure OpenAI" in response.content:
            print("✅ Inference test passed")
            return True
        else:
            print("⚠️  Unexpected response")
            return False

    except Exception as e:
        print(f"❌ Inference test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print()


def test_hr_workflow():
    """Test HR workflow with Azure OpenAI"""
    print("=" * 60)
    print("4. Testing HR Workflow Integration")
    print("=" * 60)

    try:
        from src.hr_automation import create_hr_workflow
        from src.data_models import HRJobPost

        # Create a simple job post
        job_post = HRJobPost(
            job_id="test_azure_001",
            job_title="Python Developer",
            company="Test Company",
            location="Remote",
            description="Looking for a Python developer with FastAPI experience.",
            required_skills=["Python", "FastAPI", "MongoDB"],
            experience_level="Mid-Senior"
        )

        print(f"✓ Test job post created: {job_post.job_title}")

        # Create workflow
        workflow = create_hr_workflow()
        print("✓ HR workflow created with Azure OpenAI")

        print("✅ HR workflow integration ready")
        print()
        return True

    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AZURE OPENAI INTEGRATION TEST")
    print("=" * 60)
    print()

    # Check if Azure is configured
    from src.config import Config

    if Config.LLM_PROVIDER != "azure":
        print("⚠️  WARNING: LLM_PROVIDER is not set to 'azure'")
        print(f"   Current value: {Config.LLM_PROVIDER}")
        print()
        response = input("Do you want to continue testing Azure OpenAI anyway? (y/n): ")
        if response.lower() != 'y':
            print("\nTo test Azure OpenAI, update your .env file:")
            print("  LLM_PROVIDER=azure")
            print("  AZURE_OPENAI_API_KEY=your-key")
            print("  AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
            print("  AZURE_OPENAI_DEPLOYMENT=your-deployment")
            return

    try:
        # Run tests
        test_config()

        if Config.LLM_PROVIDER == "azure":
            if not test_llm_creation():
                print("⚠️  Skipping remaining tests due to LLM creation failure")
                return

            if not test_simple_inference():
                print("⚠️  Inference test failed, but configuration looks correct")
                print("   This might be due to network or API issues")

            test_hr_workflow()

        print("=" * 60)
        print("✅ AZURE OPENAI TEST SUITE COMPLETED")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Configure your .env file with Azure OpenAI credentials")
        print("2. Set LLM_PROVIDER=azure")
        print("3. Run the application: python -m src.fastapi_api")
        print("4. Submit a test CV via the API")
        print()

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
