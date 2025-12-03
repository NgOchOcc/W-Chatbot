import asyncio
import statistics
import time
from typing import List, Dict, Any

import aiohttp
import psutil


class VLLMBenchmark:
    def __init__(self, base_url: str = "http://localhost:9292", model: str = "AlphaGaO/Qwen3-14B-GPTQ"):
        self.base_url = base_url
        self.model = model
        self.results = {
            "latency": [],
            "throughput": [],
            "time_to_first_token": [],
        }
        # Conservative settings for V100 16GB with 13GB already used
        self.max_tokens = 50  # Reduced from 100
        self.max_input_length = 100  # Keep prompts short

    async def make_request(self, messages: List[Dict[str, str]], max_tokens: int = None) -> Dict[str, Any]:
        """Make a single request to vLLM API with memory-conscious settings"""
        if max_tokens is None:
            max_tokens = self.max_tokens

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": False
        }

        async with aiohttp.ClientSession() as session:
            start_time = time.time()

            try:
                async with session.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)  # Reduced timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        end_time = time.time()

                        return {
                            "latency": end_time - start_time,
                            "response": result,
                            "tokens": len(result.get("choices", [{}])[0].get("message", {}).get("content", "").split())
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
            except asyncio.TimeoutError:
                raise Exception("Request timeout - model may be overloaded")

    async def test_single_request_latency(self, num_requests: int = 3):
        """Test single request latency with lightweight prompts"""
        print("\n📊 Testing Single Request Latency (Conservative)...")
        print(f"   Settings: max_tokens={self.max_tokens}, requests={num_requests}")

        # Short, simple prompts to minimize memory usage
        test_prompts = [
            "What is 2+2?",
            "Name three colors.",
            "Hello, how are you?"
        ]

        latencies = []
        for i in range(min(num_requests, len(test_prompts))):
            messages = [{"role": "user", "content": test_prompts[i]}]

            try:
                print(f"  Request {i + 1}/{num_requests}: '{test_prompts[i][:30]}...'")
                result = await self.make_request(messages)
                latencies.append(result["latency"])
                print(f"    Latency: {result['latency']:.3f}s, Tokens: {result['tokens']}")

                # Small delay between requests to avoid overwhelming the GPU
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"    Failed: {e}")

        if latencies:
            self.results["latency"] = {
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies) if len(latencies) > 1 else latencies[0],
                "min": min(latencies),
                "max": max(latencies),
            }

    async def test_concurrent_requests(self, num_concurrent: int = 2):
        """Test concurrent requests with very limited concurrency"""
        print(f"\n📊 Testing Concurrent Requests (n={num_concurrent}, VERY LIMITED)...")
        print("   ⚠️  Using minimal concurrency due to memory constraints")

        # Very short prompts for concurrent testing
        messages = [
            [{"role": "user", "content": f"Say '{i}'"}]
            for i in range(num_concurrent)
        ]

        tasks = []
        for msg in messages:
            # Use even smaller token limit for concurrent requests
            task = self.make_request(msg, max_tokens=20)
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]

        total_time = end_time - start_time
        self.results["throughput"] = {
            "total_requests": num_concurrent,
            "successful": len(successful),
            "failed": len(failed),
            "total_time": total_time,
            "requests_per_second": len(successful) / total_time if total_time > 0 else 0
        }

        print(f"  Completed: {len(successful)}/{num_concurrent} in {total_time:.2f}s")
        if failed:
            print(f"  Failed: {len(failed)} requests")
            for i, e in enumerate([r for r in results if isinstance(r, Exception)]):
                print(f"    Error {i + 1}: {e}")
        print(f"  Throughput: {self.results['throughput']['requests_per_second']:.2f} req/s")

    async def test_memory_limits(self):
        """Test behavior near memory limits"""
        print("\n📊 Testing Memory Limit Behavior...")
        print("   Testing with increasing token counts...")

        token_counts = [10, 25, 50]  # Very conservative
        messages = [{"role": "user", "content": "Tell me a fact."}]

        for tokens in token_counts:
            try:
                print(f"  Testing with max_tokens={tokens}...")
                result = await self.make_request(messages, max_tokens=tokens)
                print(f"    Success: {result['latency']:.3f}s")
                await asyncio.sleep(1)  # Give GPU time to free memory
            except Exception as e:
                print(f"    Failed at {tokens} tokens: {e}")
                break

    def get_system_metrics(self):
        """Get current system resource usage"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        # Try to get GPU info if nvidia-ml-py is available
        gpu_info = "GPU monitoring requires nvidia-ml-py"
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # V100
                gpu_info = {
                    "name": gpu.name,
                    "memory_used": f"{gpu.memoryUsed:.1f}MB",
                    "memory_free": f"{gpu.memoryFree:.1f}MB",
                    "memory_total": f"{gpu.memoryTotal:.1f}MB",
                    "memory_util": f"{(gpu.memoryUsed / gpu.memoryTotal) * 100:.1f}%",
                    "gpu_util": f"{gpu.load * 100:.1f}%"
                }
        except ImportError:
            pass
        except Exception as e:
            gpu_info = f"GPU monitoring error: {e}"

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024 ** 3),
            "gpu_info": gpu_info
        }

    def print_analysis(self):
        """Print analysis optimized for V100 16GB constraints"""
        print("\n" + "=" * 60)
        print("🔍 vLLM PERFORMANCE ANALYSIS - V100 16GB")
        print("=" * 60)

        print("\n⚠️  TEST CONFIGURATION:")
        print("-" * 40)
        print(f"  Model: {self.model}")
        print("  Max sequence length: 5800 (server setting)")
        print("  GPU Memory: ~13/16GB used by model")
        print(f"  Test max_tokens: {self.max_tokens}")
        print(f"  Test max_input: {self.max_input_length} chars")

        print("\n📈 PERFORMANCE METRICS:")
        print("-" * 40)

        if "latency" in self.results and self.results["latency"]:
            print("Latency Statistics:")
            for key, value in self.results["latency"].items():
                print(f"  {key.capitalize()}: {value:.3f}s")

        if "throughput" in self.results and self.results["throughput"]:
            print("\nThroughput:")
            print(f"  Requests/second: {self.results['throughput']['requests_per_second']:.2f}")
            print(
                f"Success rate: {self.results['throughput']['successful']}/{self.results['throughput']['total_requests']}") # noqa

        print("\n" + "=" * 60)
        print("✅ vLLM PROS (For Your Setup):")
        print("-" * 40)
        pros = [
            "1. GPTQ Quantization: 14B model fits in 16GB VRAM",
            "2. Efficient Memory: PagedAttention helps with limited VRAM",
            "3. Production Ready: Stable API for deployment",
            "4. OpenAI Compatible: Easy client integration",
            "5. Better than raw HF: More efficient than transformers library"
        ]

        for pro in pros:
            print(f"  {pro}")

        print("\n" + "=" * 60)
        print("⚠️  LIMITATIONS (V100 16GB Specific):")
        print("-" * 40)
        cons = [
            "1. Memory Constrained: Only ~3GB free for KV cache",
            "2. Limited Concurrency: Can handle only 1-2 concurrent requests",
            "3. Batch Size: Effectively limited to 1-2",
            "4. Long Sequences: May OOM with sequences >2000 tokens",
            "5. No Continuous Batching: Not enough memory headroom"
        ]

        for con in cons:
            print(f"  {con}")

        print("\n" + "=" * 60)
        print("🎯 RECOMMENDATIONS FOR V100 16GB:")
        print("-" * 40)
        recommendations = [
            "• Keep max_tokens low (<100) for production",
            "• Limit concurrent requests to 1-2",
            "• Monitor GPU memory closely",
            "• Consider smaller model (7B) for better concurrency",
            "• Use request queuing to prevent OOM",
            "• Set conservative timeouts",
            "• Implement retry logic with backoff"
        ]

        for rec in recommendations:
            print(f"  {rec}")

        # System metrics
        print("\n" + "=" * 60)
        print("💻 CURRENT SYSTEM METRICS:")
        print("-" * 40)
        metrics = self.get_system_metrics()
        print(f"  CPU Usage: {metrics['cpu_percent']:.1f}%")
        print(f"  RAM Available: {metrics['memory_available_gb']:.2f} GB")

        if isinstance(metrics['gpu_info'], dict):
            print(f"  GPU: {metrics['gpu_info']['name']}")
            print(
                f"    Memory: {metrics['gpu_info']['memory_used']}/{metrics['gpu_info']['memory_total']} ({metrics['gpu_info']['memory_util']})") # noqa
            print(f"    Free Memory: {metrics['gpu_info']['memory_free']}")
            print(f"    GPU Utilization: {metrics['gpu_info']['gpu_util']}")
        else:
            print(f"  GPU: {metrics['gpu_info']}")

        print("\n" + "=" * 60)
        print("💡 OPTIMIZATION TIPS:")
        print("-" * 40)
        print("  1. Start vLLM with: --max-model-len 2048 (reduce from 5800)")
        print("  2. Use: --gpu-memory-utilization 0.85 (leave headroom)")
        print("  3. Consider: --enforce-eager (disable CUDA graphs, save memory)")
        print("  4. Monitor with: nvidia-smi dmon -s mu")
        print("\n" + "=" * 60)


async def main():
    print("🚀 Starting vLLM Lightweight Benchmark for V100 16GB...")
    print("=" * 60)
    print("⚠️  Running conservative tests due to memory constraints")
    print("   Model using ~13/16GB VRAM, only ~3GB available")
    print("=" * 60)

    # Initialize benchmark
    benchmark = VLLMBenchmark()

    try:
        # Check system before starting
        print("\n🔍 Pre-test System Check:")
        metrics = benchmark.get_system_metrics()
        print(f"   CPU: {metrics['cpu_percent']:.1f}%")
        print(f"   RAM Available: {metrics['memory_available_gb']:.2f} GB")

        # Run lightweight tests
        await benchmark.test_single_request_latency(num_requests=3)

        # Small delay before concurrent test
        print("\n⏳ Waiting 2s before concurrent test...")
        await asyncio.sleep(2)

        await benchmark.test_concurrent_requests(num_concurrent=2)

        # Memory limit test
        await asyncio.sleep(2)
        await benchmark.test_memory_limits()

        # Print comprehensive analysis
        benchmark.print_analysis()

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check vLLM server: curl http://localhost:9292/v1/models")
        print("2. Monitor GPU: nvidia-smi")
        print("3. Reduce max_tokens if OOM")
        print("4. Restart vLLM with lower --max-model-len")


if __name__ == "__main__":
    asyncio.run(main()
                )
