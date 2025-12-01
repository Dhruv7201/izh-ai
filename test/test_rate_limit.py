"""
Test script to verify rate limiting implementation.
Run this after starting the server to test rate limits.
"""
import httpx
import asyncio
import time


async def test_rate_limit():
    """Test rate limiting on chat endpoints."""
    base_url = "http://localhost:8000"
    
    print("Testing rate limit on /chat/simple endpoint (20/minute limit)...")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        success_count = 0
        rate_limited_count = 0
        
        # Try to make 25 requests (should hit rate limit after 20)
        for i in range(1, 26):
            try:
                response = await client.post(
                    f"{base_url}/chat/simple",
                    params={"prompt": f"Test request {i}"}
                )
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"Request {i}: ✓ Success (Status: {response.status_code})")
                    
                    # Print rate limit headers
                    if "x-ratelimit-limit" in response.headers:
                        print(f"  Rate Limit: {response.headers.get('x-ratelimit-limit')}")
                        print(f"  Remaining: {response.headers.get('x-ratelimit-remaining')}")
                        print(f"  Reset: {response.headers.get('x-ratelimit-reset')}")
                        
                elif response.status_code == 429:
                    rate_limited_count += 1
                    print(f"Request {i}: ✗ Rate Limited (Status: {response.status_code})")
                    print(f"  Response: {response.text}")
                else:
                    print(f"Request {i}: ? Unexpected (Status: {response.status_code})")
                    
            except Exception as e:
                print(f"Request {i}: Error - {str(e)}")
            
            # Small delay between requests
            await asyncio.sleep(0.1)
    
    print("-" * 60)
    print(f"\nResults:")
    print(f"  Successful requests: {success_count}")
    print(f"  Rate limited requests: {rate_limited_count}")
    print(f"  Total requests: {success_count + rate_limited_count}")
    
    if rate_limited_count > 0:
        print("\n✓ Rate limiting is working correctly!")
    else:
        print("\n⚠ Rate limiting may not be configured properly.")


async def test_health_endpoint():
    """Test rate limiting on health check endpoint."""
    base_url = "http://localhost:8000"
    
    print("\n\nTesting rate limit on /health endpoint (100/minute limit)...")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        # Try 10 requests quickly
        for i in range(1, 11):
            try:
                response = await client.get(f"{base_url}/health")
                status = "✓" if response.status_code == 200 else "✗"
                print(f"Request {i}: {status} (Status: {response.status_code})")
                
                if i == 10 and "x-ratelimit-remaining" in response.headers:
                    remaining = response.headers.get('x-ratelimit-remaining')
                    print(f"\nRemaining requests: {remaining}/100")
                    
            except Exception as e:
                print(f"Request {i}: Error - {str(e)}")


if __name__ == "__main__":
    print("Rate Limiting Test Script")
    print("=" * 60)
    print("\nMake sure the server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel\n")
    
    try:
        time.sleep(2)
        asyncio.run(test_rate_limit())
        asyncio.run(test_health_endpoint())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
